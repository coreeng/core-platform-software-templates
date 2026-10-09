# Next.js / Java notes proof template

This independent application slice proves a Next.js → Spring Boot JDBC → PostgreSQL
path. It is not a released workspace-compatible product. NFT is unsupported, and
live GitHub Fast Feedback, Extended Test and Prod are separate approval gates.

## Verification

From the software-template repository root:

```sh
make templates-validate
make test-nextjs-java-structure
make test-nextjs-java-render
make test-nextjs-java-runner
make test-nextjs-java-build
make test-nextjs-java-functional
```

General `templates-validate` runs the fixture-free `test-nextjs-java-structure`
gate: strict structural rendering plus offline runner regressions. It ignores
`P2P_HELPER_DIR`, so an unavailable local fixture does not break general CI.
Structural success does **not** qualify the P2P helper or its stage contracts.
`test-nextjs-java-render` is the separate full qualification gate and requires
the actual reviewed fixture (explicitly supplied or discovered in a sibling repo).

The build/functional targets invoke `tests/nextjs_java_local.py`. Ordinary Docker
builds pass a fresh `UNIT_TEST_NONCE` build argument immediately before each unit
test step, so dependency layers remain cacheable but test execution is not.
The Gradle wrapper runs backend tests with `--rerun-tasks` and prints actual
passed/failed/skipped counts; Jest prints frontend counts. They build five images (two applications plus
functional/integration/extended browser images). Functional verification creates
an isolated, nonce-labelled network and containers, creates notes through a real
Chromium UI and HTTP API, validates Unicode limits, refreshes and reloads, restarts
both applications and PostgreSQL, then verifies persistence. It removes only its
returned IDs and test-owned UUID records. Creation reserves unique names/tags
before starting Docker. Failure, timeout and interruption recovery inspects only
those reservations and refuses foreign nonce labels or changed identities.
SIGINT/SIGTERM unwind into cleanup; child process groups receive TERM then bounded
KILL escalation and are reaped. Cleanup has separate container/network/volume/image
budgets and continues after individual failures. PostgreSQL storage is an explicitly
created, nonce-labelled volume with a recorded creation fingerprint. Image cleanup
removes only reserved tags without force-deleting unrelated aliases. No Compose, Testcontainers, host socket
mounts, credential mounts, existing-name adoption or daemon configuration changes.
The Docker client uses an ephemeral auth-free config and the existing daemon endpoint.

## Complete pin inventory

| Scope | Pins / source |
| --- | --- |
| Frontend | Node `26.10.0-alpine3.24`, Yarn `4.18.1`, Next `16.3.6`, React/DOM `19.3.0`, `prom-client 15.1.3`; every dev dependency and security resolution in `frontend/package.json` and canonical `yarn.lock` |
| Backend | Gradle `9.8.0-jdk26-noble` (digest pinned), Temurin `26.0.2.1_1-jre-noble`, JDK `26`, Spring Boot `4.1.1`, dependency-management `1.1.7`, Logback `1.6.4`, Jackson BOMs `2.22.3` / `3.1.7`; Boot BOM manages PostgreSQL JDBC/Flyway/Micrometer versions |
| Gradle wrapper | All four wrapper files copied from `java/web`, distribution `9.8.0`, SHA256 `bafd5ce9cfaea0fbccfdc8439a1ac42fbd4cd9c89dc9a988228d8a2639a58e6c`; Docker builds invoke `./gradlew` on JDK 26 |
| Browser tests | Node `26.10.0-bookworm-slim`, Yarn `4.18.1`, Playwright package and noble image `1.63.0`, canonical `p2p/tests/yarn.lock` |
| Deployment | Both aliased `core-platform-app` dependencies `0.18.0`, generated `Chart.lock`, vendored archive SHA256 `2e85aedc9272c9fb861784e0b1c7f9529298f51f4721e36d8f8e3d1282e0f6eb`, official PostgreSQL `18.0-bookworm` |
| Render tests | Isolated test-only Jinja2 `3.1.6`, PyYAML `6.0.3` |
| Validation gates | General structure/offline runner checks require no helper; full render/stage qualification requires the actual local Task8 fixture, never a guessed released pin |
| Docker client fallback | macOS ARM64 only: stable buildx `v0.38.0`, SHA256 `85989b895add5f119c1ccf8eada2f6892fc33ccf16bd8917638eae404ef26344`, installed into the temporary client config only when the existing plugin is unavailable |

Update each manifest and regenerate its lock with Yarn 4; run immutable installs
and the structure, full qualification, build and functional gates afterwards.
The stable private package name `app` prevents
rendered names from changing canonical workspace ordering. Render the chart into
a temporary directory before `helm dependency update`; copy back only the generated
lock and exact archive, verify its digest against the published repository index,
and keep Helm native expressions inside Jinja `{% raw %}` blocks.

No helper release pin is invented: `P2P_HELPER_DIR` must explicitly identify the
reviewed local Task8 fixture containing `p2p.mk`, `p2p-build.mk` and
`scripts/build-image.sh`. CI/workspace qualification awaits a released contract.

For reproducible stage-contract verification, run from the repository root:

```sh
P2P_HELPER_DIR=/absolute/path/to/reviewed/p2p-fixture make test-nextjs-java-render
python3 -B -m unittest discover -s tests -p 'nextjs_java_runner_test.py' -v
```

The render gate can discover the actual fixture in a sibling `p2p` repository
(including its `.worktrees/local-development-workspaces` checkout), using Git's
common directory rather than a workstation-specific path. An incomplete explicit
fixture fails. If no actual fixture exists, structural checks run but the full
gate fails as **UNQUALIFIED**, never silently skips the stage contract. To request
only structural checks explicitly, run `make test-nextjs-java-structure` or
`bash tests/nextjs_java_template_test.sh --pure-render`; the shell wrapper creates
the isolated Jinja2/PyYAML test environment as needed. It reports the helper gate
as skipped/unqualified, even if an unavailable `P2P_HELPER_DIR` is set.
