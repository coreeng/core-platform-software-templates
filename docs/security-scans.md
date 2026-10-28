# Template security validation

Run the same commands on a developer machine and on a CI runner. Nothing in this
workflow pushes images, provisions infrastructure or deploys applications.

Prerequisites: Python 3.11+, Node 22+, Ruby (for P2P YAML parsing), Make, Git, curl,
and Docker with Buildx. Linux and macOS on AMD64/ARM64 are supported by the Trivy
and TruffleHog installer. Docker must share the worktree directory on macOS.

```sh
make security-setup security-tools
make security-test
make security-all
```

`security-setup` creates an isolated Python environment. `security-tools` installs
Trivy 0.75.0 and TruffleHog 3.99.0 from official releases, verifying the SHA-256
hashes committed in `scripts/security/tools.json`. The versions and ignore helper
match P2P commit `aa1278b53ce1b1fa9d5409f58d5b921e4599a32d`. Generated Makefiles use
that same immutable P2P revision during audit builds. Update the pins and vendored
helper together after comparing upstream policy changes.

The runner discovers Git-tracked and non-ignored new template definitions and every
skeleton Dockerfile. Today this is 11 templates and 36 images. Unknown Dockerfile layouts
or missing concrete Make targets fail rather than silently reducing coverage.
Rendering uses strict Jinja substitution, preserves binary files and executable
bits, and leaves the original skeletons unchanged. Builds use the templates'
`build-*` Make targets, including their lint prerequisites.

## Individual commands

| Command | What it does |
|---|---|
| `make security-list` | Emits a JSON template list for a CI matrix |
| `make security-render` | Renders clean isolated copies and records inventory |
| `make security-source` | Scans each rendered template with Trivy vulnerability/license analysis and TruffleHog filesystem secret detection |
| `make security-history` | Scans repository history reachable from HEAD for secrets |
| `make security-build` | Builds all app, infrastructure runner and test images; records image IDs, platforms and input fingerprints |
| `make security-images` | Scans those immutable image IDs with Trivy and TruffleHog |
| `make security-all` | Runs history, then source/build/image scans one template at a time, continuing to collect results after individual failures |
| `make security-codeql` | Runs default CodeQL query suites against rendered code and workflows |
| `make security-test` | Tests inventory, rendering, redaction, suppressions and failure behavior |

To narrow a local run or shard CI:

```sh
make security-build security-images SECURITY_TEMPLATE=nextjs/web
make security-source SECURITY_BLOCKING_SEVERITY=low
make security-history SECURITY_BASE=origin/main
make security-build security-images SECURITY_PLATFORM=linux/amd64
```

`SECURITY_TEMPLATE` must exactly match a discovered template. By default builds
use the host's Linux architecture; the supplied CI workflow builds AMD64. Run
separately for each production architecture, with different `SECURITY_DIR`
directories if retaining both sets of evidence. Scanning rejects manifests whose
source fingerprint or platform differs from the current request. A selected
build replaces its build manifest; rerun the corresponding build before scanning
another selection. Do not run rendering, building and scanning concurrently in
the same `SECURITY_DIR`.

The default state directory is `.security/` (ignored by Git). Override it with
`SECURITY_DIR`, and optionally put binaries elsewhere with `SECURITY_TOOLS_DIR`.
`SECURITY_TIMEOUT` sets the per-command timeout in seconds (default 1800).
`security-all` removes its own image tags after scanning each template to bound
local disk use. Set `SECURITY_KEEP_IMAGES=true` to retain them. Standalone
`security-build` retains images for a later `security-images` invocation. BuildKit
cache is owned by the selected builder and is not pruned automatically.

Existing Docker context, `DOCKER_HOST`, `DOCKER_CONFIG` and `BUILDX_BUILDER`
settings are honored.

## Results and policy

Reports are under `.security/reports/`, with separate JSON and Markdown summaries
for each command. Per-target JSON contains active and ignored findings, the
scanner versions, timestamp, source fingerprint, image ID and platform where
applicable. Trivy reports retain package/advisory evidence while excluding container
environment variables and build history. Summaries record Trivy DB
metadata. Build logs are under `.security/logs/`; `.security/builds.json` records
the exact build inventory. Reports represent advisories known at scan time.

The default blocking threshold is **high**. `SECURITY_BLOCKING_SEVERITY` accepts
`off`, `low`, `medium`, `high`, or `critical`. Even with `off`, scanner failures
fail the command. The underlying Python process returns 0 for a completed pass,
1 for blocking findings, and 2 for failed/incomplete execution. Make reports a
nonzero recipe exit as its own failure status; inspect the JSON to distinguish
findings from execution failure.

All vulnerability severities and **unfixed vulnerabilities** are retained. This
is intentionally more complete than P2P's default `ignore-unfixed=true`.
`.p2p-security-ignore.yaml` uses P2P's exact matching and expiry implementation;
suppressed findings remain in `ignored`, and expired entries no longer suppress.
Image entries match rendered P2P names: the application name for `app`,
`<name>-functional`, `<name>-integration`, `<name>-nft` and `<name>-extended`.
Licenses are reported without a blocking license policy, matching P2P.

TruffleHog verification is enabled, as in P2P: suspected credentials may be
checked against their issuing services. Verified secrets follow critical-severity
policy. Unverified and unknown results remain visible for manual assessment.
Secret values and arbitrary scanner fields are never copied into reports.
Raw secret output and scanner stderr live only in private temporary directories
that are removed on completion or failure. Reports retain detector, status,
fingerprint and location. Do not upload the entire `.security` directory.

An image with no filesystem layers (currently the monitoring app's `FROM scratch`
placeholder) is explicitly `not-applicable`; the monitoring integration image is
still scanned. Scanning template sources does not resolve every build-time
dependency, so the built-image scans are required as well. External images pulled
by Helm charts, uninstalled infrastructure provider binaries, deployed systems,
and dependencies present only in discarded builder stages are outside this
inventory. A green result does not establish absence of all vulnerabilities.

## CodeQL

Install the official CodeQL **2.27.3 bundle including query packs**, then put its
`codeql` executable on PATH or set `CODEQL=/absolute/path/to/codeql`:

```sh
make security-codeql
```

Use a host supported by that CodeQL distribution and install the Go toolchain
required by the template modules. See [CodeQL setup](https://docs.github.com/en/code-security/codeql-cli/getting-started-with-the-codeql-cli/setting-up-the-codeql-cli).
This optional target is separate from `security-all` because CodeQL has its own
platform, toolchain and licensing requirements. It writes SARIF and extraction
logs alongside reports. It uses the default suites for Actions, Java/Kotlin,
JavaScript/TypeScript, Python and Go; Go uses autobuild and other languages use
no-build extraction. Each Go module gets its own database to avoid relying on
monorepo autodetection. Inspect extraction diagnostics as well as findings.
CodeQL findings fail this target independently of the Trivy severity threshold.

## CI

`.github/workflows/security.yaml` runs on pull requests and manual dispatch. It
calls these exact Make targets: a source/history job and a dynamically discovered
image matrix with at most two concurrent jobs. Fail-fast is disabled, and reports
are uploaded even when scanners or finding policies fail. Jobs use read-only
repository permissions and no deployment credentials. Images are loaded into the
job's local Docker engine; no registry push is needed.

GitHub's existing CodeQL default setup remains a separate PR check. Any CI system
with the prerequisites can run `security-codeql` as another job. A passing source
job alone does not stand in for the image matrix or CodeQL.

This tooling adds maintainer validation without changing generated application
behavior, Portal capabilities, deployment journeys or product architecture.
