# AGENTS.md — Core Platform Software Templates

## Repository layout

```
<root>/
├── go/web          — Go (Gin) web service
├── java/web        — Java (Spring Boot) web service
├── nextjs/web      — Next.js web application
├── python/web      — Python (FastAPI) web service
├── docker/web      — Generic Docker web service (podinfo reference image)
├── static/nextra   — Nextra static documentation site
└── infra/
    ├── cloudsql    — Cloud SQL infrastructure (OpenTofu)
    ├── tofu        — Generic OpenTofu infrastructure
    └── urlrouter   — URL router infrastructure
```

Each template contains a `template.yaml` and a `skeleton/` directory copied verbatim into a
new project at instantiation time. Every text file in `skeleton/` has Jinja2-style variables
substituted:

| Variable | Description |
|---|---|
| `{{ name }}` | Application/infrastructure name — must be a valid Kubernetes DNS label (lowercase alphanumeric and hyphens only) |
| `{{ tenant }}` | Tenant name |
| `{{ version_prefix }}` | Optional version prefix |
| `{{ working_directory }}` | Optional path filter for GitHub Actions triggers |

---

## App templates

App templates (`kind: app`) deploy containerised web services. Each contains:

- `template.yaml` — `kind: app`, replica count, CPU/memory limits
- `skeleton/Makefile` — P2P targets: `p2p-build`, `p2p-functional`, `p2p-nft`, `p2p-integration`, `p2p-extended-test`, `p2p-prod`
- `skeleton/.github/workflows/` — `fast-feedback.yaml`, `extended-test.yaml`, `prod.yaml`
- `skeleton/p2p/config/` — Helm config per P2P stage (`common.yaml` + per-stage overrides)
- `skeleton/p2p/tests/` — BDD test containers (functional, integration, extended) and NFT (K6)
- `skeleton/p2p/scripts/helm-test.sh` — Helm test runner

### Updating app template dependencies

> **macOS vs Linux `sed -i`:** Commands below use GNU syntax (Linux/CI). On macOS add an
> empty-string suffix: `sed -i '' 's/old/new/' file`.

> **Before updating any image tag:** verify the exact tag exists on the registry (Docker Hub,
> GHCR, MCR, etc.) and is a stable GA release — not an alpha, beta, or RC. Check the
> upstream project's release page to confirm.
>
> **Alpine version:** always use the **latest Alpine version** the image supports — check Docker
> Hub for the newest `X.Y.Z-alpineA.B` tag rather than keeping the version already in the template.

#### Complete version-pin inventory

Every hardcoded version in the app templates. Use this as a completion checklist when updating.

| Template | File | Pins | Reference |
|---|---|---|---|
| `go/web` | `skeleton/go.mod` | Go version | [golang.org/dl](https://golang.org/dl) |
| `go/web` | `skeleton/Dockerfile` | `golang:X.Y.Z-alpineA.B` (build), `alpine:A.B` (runtime) | matches `go.mod`; latest Alpine |
| `go/web` | `skeleton/Makefile` (`lint-app`) | `golang:X.Y.Z-alpineA.B`, `revive@vX.Y.Z` | same Go image; [mgechev/revive releases](https://github.com/mgechev/revive/releases) |
| `go/web` | `p2p/tests/functional/go.mod` | Go version, all deps including `godog` | `go get -u` |
| `go/web` | `p2p/tests/functional/Dockerfile` | `golang:X.Y.Z-alpineA.B`, `godog@vX.Y.Z` | matches `functional/go.mod` |
| `go/web` | `p2p/tests/integration/go.mod` | Go version, all deps including `godog` | `go get -u` |
| `go/web` | `p2p/tests/integration/Dockerfile` | `golang:X.Y.Z-alpineA.B`, `godog@vX.Y.Z` | matches `integration/go.mod` |
| `java/web` | `skeleton/gradle/wrapper/gradle-wrapper.properties` | `distributionUrl` Gradle version | must match `gradle:X.Y.Z-jdkNN-noble` in Dockerfile; regenerate all wrapper files (see below) |
| `java/web` | `skeleton/service/build.gradle` | Spring Boot, Spring DM, SpringDoc, Guava, HikariCP, `sourceCompatibility`/`targetCompatibility` | [spring.io](https://spring.io/projects/spring-boot), Maven Central |
| `java/web` | `skeleton/Dockerfile` | `gradle:X.Y.Z-jdkNN-noble` (build), `eclipse-temurin:NN-jre-noble` (runtime) | [Docker Hub gradle](https://hub.docker.com/_/gradle), [eclipse-temurin](https://hub.docker.com/_/eclipse-temurin) |
| `java/web` | `p2p/tests/functional/build.gradle` | JUnit BOM, Cucumber, REST Assured, JSONAssert | Maven Central |
| `java/web` | `p2p/tests/functional/Dockerfile` | `gradle:X.Y.Z-jdkNN-noble` | matches main Dockerfile |
| `java/web` | `p2p/tests/integration/build.gradle` | JUnit BOM, Cucumber, REST Assured, JSONAssert | Maven Central |
| `java/web` | `p2p/tests/integration/Dockerfile` | `gradle:X.Y.Z-jdkNN-noble` | matches main Dockerfile |
| `nextjs/web` | `skeleton/package.json` | all npm deps | `npx npm-check-updates` |
| `nextjs/web` | `skeleton/Dockerfile` | `node:X.Y.Z-alpineA.B` | Node major from `engines` in `package.json`; latest Alpine; keep in sync with `@types/node` major |
| `nextjs/web` | `p2p/tests/functional/package.json` | Cucumber, Playwright | `npx npm-check-updates` |
| `nextjs/web` | `p2p/tests/functional/Dockerfile` | Playwright image | matches `@playwright/test` version |
| `static/nextra` | `skeleton/package.json` | all npm deps | `npx npm-check-updates` |
| `static/nextra` | `skeleton/Dockerfile` | `node:X.Y.Z-alpineA.B` | Node major from `engines` in `package.json`; latest Alpine; keep in sync with `@types/node` major |
| `static/nextra` | `p2p/tests/functional/package.json` | Cucumber, Playwright | `npx npm-check-updates` |
| `static/nextra` | `p2p/tests/functional/Dockerfile` | Playwright image | matches `@playwright/test` version |
| `python/web` | `skeleton/pyproject.toml` | all Python deps | `uv lock` |
| `python/web` | `skeleton/uv.lock` | locked Python deps | `uv lock` |
| `python/web` | `skeleton/Dockerfile` | `python:X.Y-slim` (both stages), `ghcr.io/astral-sh/uv:X.Y.Z` | matches `requires-python`; [astral-sh/uv releases](https://github.com/astral-sh/uv/releases) |
| `python/web` | `p2p/tests/functional/Dockerfile` | `python:X.Y-slim`, `behave`, `requests` | match main Dockerfile; pin behave/requests |
| `python/web` | `p2p/tests/integration/Dockerfile` | `python:X.Y-slim`, `behave`, `requests` | match main Dockerfile; pin behave/requests |
| `docker/web` | `skeleton/Dockerfile` | `stefanprodan/podinfo:X.Y.Z` | [podinfo releases](https://github.com/stefanprodan/podinfo/releases) |
| `docker/web` | `p2p/tests/{functional,integration,extended}/go.mod` | Go version, all deps | `go get -u` |
| `docker/web` | `p2p/tests/{functional,integration,extended}/Dockerfile` | `golang:X.Y.Z-trixie` | Go version in `go.mod` |
| **all** | `p2p/tests/nft/Dockerfile` | `golang:X.Y.Z-alpineA.B`, `prom/prometheus:vX.Y.Z`, `alpine:A.B`, `xk6@vX.Y.Z`, `xk6-prometheus@vX.Y.Z` | see [NFT tests](#nft-tests-all-templates) below |

#### Update all test dependencies

When updating app template dependencies, **also update every test module** for each template.
Find them under `p2p/tests/` — update each subdirectory (functional, integration, extended, nft)
that contains dependency files for that template.

#### go/web

```bash
cd go/web/skeleton
go get -u ./...
go mod tidy
```

Update each test module (replace `X.Y.Z` with the Go version from the main `go.mod`):

```bash
for dir in p2p/tests/functional p2p/tests/integration; do
  (cd go/web/skeleton/"$dir" && go get -u ./... && go mod edit -go=X.Y.Z && go mod tidy)
done
```

Update all image and version pins from the inventory table. The `godog@vX.Y.Z` pin in each test Dockerfile must match the version resolved into that directory's `go.mod` by the step above.

#### java/web

When upgrading Gradle, regenerate the wrapper scripts and jar (not just the `.properties` file):

```bash
docker run --rm -v "$(pwd)/java/web/skeleton:/project" -w /project \
  docker.io/gradle:9.3.1-jdk25-noble gradle wrapper --gradle-version 9.3.1
```

This updates `gradlew`, `gradlew.bat`, and `gradle/wrapper/gradle-wrapper.jar` in addition to `gradle-wrapper.properties`.

Edit versions in `skeleton/service/build.gradle`, then validate:

```bash
cd java/web/skeleton
./gradlew dependencies
```

Also update test dependencies in `p2p/tests/functional/build.gradle` and
`p2p/tests/integration/build.gradle` — these are independent Gradle modules not managed by the
Spring Boot BOM: JUnit BOM, Cucumber, REST Assured, JSONAssert.

When upgrading the JDK version (e.g. 21 → 25), also update `sourceCompatibility` and
`targetCompatibility` in `build.gradle` to match, and update the `gradle:X.Y.Z-jdkNN-noble`
build image and `eclipse-temurin:NN-jre-noble` runtime image in `skeleton/Dockerfile` and the
test Dockerfiles to the same JDK version. Gradle 9+ has no alpine variant for JDK 25 — use
`-noble` (Ubuntu) instead.

#### nextjs/web and static/nextra

`package.json` contains `"name": "{{ name }}"` which is not a valid npm name — substitute temporarily:

```bash
cd <template>/skeleton
sed -i 's/"name": "{{ name }}"/"name": "app"/' package.json
npx npm-check-updates -u
yarn install
sed -i 's/"name": "app"/"name": "{{ name }}"/' package.json
```

For `nextjs/web` and `static/nextra` — also update `p2p/tests/functional/package.json` (no
`{{ name }}` substitution needed; for `static/nextra`, temporarily set parent `package.json`
`name` to a valid value so `yarn install` can run):

```bash
# nextjs/web:
cd nextjs/web/skeleton/p2p/tests/functional
npx npm-check-updates -u && yarn install

# static/nextra (temporarily set parent package.json "name" to valid value first):
cd static/nextra/skeleton/p2p/tests/functional
npx npm-check-updates -u && yarn install
```

Match the Playwright image in `p2p/tests/functional/Dockerfile` to the `@playwright/test`
version in `functional/package.json`.

Update `skeleton/Dockerfile`: `node:X.Y.Z-alpineA.B` — match Node major to `engines` in
`package.json`; use latest Alpine variant. When changing Node major, also update `@types/node`
to the same major (e.g. `^26.0.0`) so types stay aligned with the runtime.

#### python/web

`pyproject.toml` and `uv.lock` both contain `name = "{{ name }}"` — substitute temporarily:

```bash
cd python/web/skeleton
sed -i 's/name = "{{ name }}"/name = "app"/' pyproject.toml uv.lock
uv lock
sed -i 's/name = "app"/name = "{{ name }}"/' pyproject.toml
# Restore only the [[package]] entry that has source = { editable = "." }
sed -i '/source = { editable = "\." }/{x;s/name = "app"/name = "{{ name }}"/;x}' uv.lock
```

Update `skeleton/Dockerfile`: `python:X.Y-slim` (both stages), `ghcr.io/astral-sh/uv:X.Y.Z` —
match to `requires-python` in `pyproject.toml`.

Also update `behave` and `requests` versions in the functional/integration test Dockerfile
`pip install` line; match `python:X.Y-slim` to the main Dockerfile.

#### docker/web

Update the image tag directly in `skeleton/Dockerfile` (`stefanprodan/podinfo:X.Y.Z`).

Update each test module (replace `X.Y.Z` with the same Go version used in `go/web`):

```bash
for dir in p2p/tests/functional p2p/tests/integration p2p/tests/extended; do
  (cd docker/web/skeleton/"$dir" && go get -u ./... && go mod edit -go=X.Y.Z && go mod tidy)
done
```

#### NFT tests (all templates)

The NFT Dockerfile builds a custom K6 binary with `xk6-prometheus`.
Keep these versions consistent across all templates and update them together:

- Go builder: `golang:X.Y.Z-alpineA.B` — use the **same Go version** as the main `go/web` Dockerfile and use the **latest Alpine variant** (check Docker Hub for the newest `X.Y.Z-alpineA.B` tag)
- Prometheus (`promtool`): `prom/prometheus:vX.Y.Z` — **do not upgrade to v3.x, not yet supported; keep on latest v2.x**
- Alpine runtime: `alpine:A.B` — use the **same Alpine version** as the Go builder above
- `xk6`: `go install go.k6.io/xk6@vX.Y.Z` — check [grafana/xk6 releases](https://github.com/grafana/xk6/releases) for the latest tag (root package since v1.0.0, not `cmd/xk6`)
- `xk6-prometheus`: `xk6 build --with github.com/coreeng/xk6-prometheus@vX.Y.Z` — check [coreeng/xk6-prometheus releases](https://github.com/coreeng/xk6-prometheus/releases) for the latest tag

**Extended tests** — currently placeholders; update the base image to match the template's other test images.

#### After updating: verify no stale pins

Scan for any remaining old version strings before committing. Adjust the pattern to match the
versions you replaced (example for a Go 1.25.x → 1.26.0 / alpine3.22 → 3.23 update):

```bash
rg 'golang:1\.25\.|alpine3\.22|alpine:3\.22' --glob '*.{Dockerfile,toml,mod,gradle}'
```

### Local Docker smoke test

After adding a new template or updating dependencies/images, verify the build locally.
Because `skeleton/` contains `{{ name }}` placeholders, use a throwaway copy:

```bash
tmpdir=$(mktemp -d)
cp -r <language>/web/skeleton/. "$tmpdir"
# Substitute all template variables; LC_ALL=C avoids sed failures on binary files
grep -rl '{{' "$tmpdir" | while IFS= read -r f; do
  LC_ALL=C sed -i '' \
    -e 's/{{ name }}/myapp/g' \
    -e 's/{{ tenant }}/mytenant/g' \
    -e 's/{{ version_prefix }}//g' \
    -e 's/{{ working_directory }}//g' \
    "$f"
done
docker build -t myapp-test "$tmpdir"
```

Each template exposes different ports and health endpoints:

| Template | Port flags | Sleep | Endpoints (expected response) |
|---|---|---|---|
| `go/web`, `python/web` | `-p 8080:8080 -p 8081:8081` | 3s | `:8080/hello` → "Hello world"; `:8081/internal/status`; `:8081/metrics` |
| `java/web` | `-p 8080:8080 -p 8081:8081` | 8s | `:8080/hello` → "Hello World!"; `:8081/health` → `{"status":"UP"}`; `:8081/prometheus` |
| `nextjs/web`, `static/nextra` | `-p 3000:3000` | 5s | `:3000/readyz` → "OK"; `:3000/livez` → "OK" |
| `docker/web` | `-p 9898:9898` | 2s | `:9898/healthz` → `{"status":"OK"}`; `:9898/readyz` → `{"status":"OK"}` |

```bash
docker run --rm <PORT_FLAGS> --name myapp myapp-test &
sleep <SLEEP>
# curl each endpoint from the table above
docker stop myapp
```

#### Test container images

The application image smoke test above does not cover the test containers. After updating
dependencies or images, also build every test container Dockerfile directly from its own
directory (no template-variable substitution needed — test directories contain no `{{}}`
placeholders):

```bash
BASE=<template>/skeleton   # e.g. go/web/skeleton
docker build -t test-functional  "$BASE/p2p/tests/functional"
docker build -t test-integration "$BASE/p2p/tests/integration"
docker build -t test-nft         "$BASE/p2p/tests/nft"
docker build -t test-extended    "$BASE/p2p/tests/extended"
docker rmi test-functional test-integration test-nft test-extended
```

Repeat for every template you changed. Notable caveats:

| Template | Stage | Base image | Notes |
|---|---|---|---|
| `java/web` | functional, integration | `gradle:X.Y.Z-jdkNN-noble` | slow on first run (downloads Gradle wrapper + all deps) |
| `nextjs/web`, `static/nextra` | functional | `mcr.microsoft.com/playwright:vX.Y.Z-noble` | large image (~1.5 GB) |
| `docker/web` | functional, integration, extended | `golang:X.Y.Z-trixie` | Go-based BDD tests (note `-trixie`, not `-alpine`) |
| **all** | nft | `golang:X.Y.Z-alpineA.B` | builds custom k6 binary with `xk6-prometheus` |

> **xk6 install path:** for `xk6 >= v1.0.0` the main package moved to the module root —
> use `go install go.k6.io/xk6@vX.Y.Z`, **not** `go install go.k6.io/xk6/cmd/xk6@vX.Y.Z`.
> Verify the correct path in the [release notes](https://github.com/grafana/xk6/releases)
> when doing a major version bump.

### Adding a new app template

Use `go/web` as the reference.

#### 1. Create `template.yaml`

```yaml
name: <language>-web
description: <Language> web application
kind: app
skeletonPath: ./skeleton
config:
  replicas: 2
  resources:
    limits:
      cpu: 250m      # use 1000m for JVM-based languages
      memory: 512Mi  # use 1024Mi for JVM-based languages
```

#### 2. Copy shared files verbatim from `go/web/skeleton`

| File | Notes |
|---|---|
| `.editorconfig` | |
| `.github/workflows/fast-feedback.yaml` | |
| `.github/workflows/extended-test.yaml` | |
| `.github/workflows/prod.yaml` | |
| `p2p/scripts/helm-test.sh` | |
| `p2p/tests/nft/Dockerfile` | Do not update versions independently of other templates |
| `p2p/tests/nft/resources/load-testing/hello.js` | |
| `p2p/tests/nft/resources/load-testing/validate.sh` | |
| `p2p/config/functional.yaml` | Empty |
| `p2p/config/integration.yaml` | Empty |
| `p2p/config/nft.yaml` | Empty |
| `p2p/config/extended-test.yaml` | Empty |
| `p2p/config/prod.yaml` | Empty |

#### 3. Adapt the Makefile

Copy from `go/web/skeleton/Makefile`. Change only the `lint-app` target to use the
language's own linter.

#### 4. Create `p2p/config/common.yaml`

Copy from `go/web/skeleton/p2p/config/common.yaml`. The ports are correct for all templates:

- Liveness probe: port 8081, path `/internal/status`
- Readiness probe: port 8080, path `/hello`
- Metrics scraping: port 8081

#### 5. Implement the two-port application

Every app template exposes two ports:

| Port | Purpose | Ingress-exposed? |
|---|---|---|
| 8080 | Application traffic (`GET /hello`) | Yes |
| 8081 | Internal ops (`GET /metrics`, `GET /internal/status`) | No |

The port separation prevents metrics and health endpoints from being accidentally exposed
publicly. The `/hello` endpoint must return a body containing `"Hello world"` — this is what
the K6 NFT script asserts.

Use the framework's lightest available Prometheus metrics library. Avoid per-request
middleware with significant overhead (e.g. full OpenTelemetry tracing instrumentation) —
the NFT test targets 1000 req/s at 2 replicas × 250m CPU with p(99) < 2000ms.

#### 6. Implement functional and integration BDD tests

Copy the Gherkin feature files from `go/web` (the scenarios are language-agnostic HTTP
checks). Use the language's standard Cucumber library. Keep the test Dockerfile minimal —
BDD runner and HTTP client only.

#### 7. Add a placeholder extended test Dockerfile

Use the same Alpine version as the rest of the template (check the current version in
`p2p/tests/nft/Dockerfile`):

```dockerfile
FROM docker.io/alpine:3.23
ENTRYPOINT ["echo"]
CMD ["### extended tests not implemented ###"]
```

#### 8. Handle `{{ name }}` in lockfiles

If the package manager embeds the project name in its lockfile (e.g. `uv.lock`), store
`{{ name }}` in the lockfile too — the template engine substitutes all files in `skeleton/`.
Add dependency-update instructions to this file following the `python/web` pattern.

Lockfiles that do not embed the project name (e.g. `yarn.lock`, `go.sum`) need no special
handling. Always commit the lockfile; do not `.gitignore` it.

#### 9. Smoke-test and validate

Run the [local Docker smoke test](#local-docker-smoke-test), then validate all three P2P
pipeline stages against a real cluster:

| Stage | What runs |
|---|---|
| `fast-feedback` | Build, unit tests, functional BDD tests |
| `extended-test` | Integration BDD tests, NFT (K6 load test) |
| `prod` | Production deployment |

The NFT stage is the most likely to fail — see step 5 above regarding per-request overhead.

#### 10. Update this file

Add the new template to the repository layout diagram and add dependency-update and
Dockerfile-sync entries in the relevant sections above.

---

## Infra templates

Infra templates (`kind: infra`) provision cloud infrastructure using OpenTofu and Terragrunt.
Each contains:

- `template.yaml` — `kind: infra`, no `config` block (no replicas or resource limits)
- `skeleton/Dockerfile` — OpenTofu runner container (the "app" that applies infrastructure)
- `skeleton/Makefile` — `p2p-build` and `deploy-*` targets; no BDD/NFT/integration test targets
- `skeleton/.github/workflows/` — `fast-feedback.yaml`, `prod.yaml`
- `skeleton/p2p/config/` — per-environment config (`common.yaml` + per-stage overrides)
- `skeleton/infrastructure/code/` — OpenTofu modules and Terragrunt configuration
  - `versions.tf` — OpenTofu version constraint and provider versions
  - `.terraform.lock.hcl` — provider lock file (equivalent to `go.sum`); always committed

### Updating infra template versions

> **TODO:** Add instructions for updating OpenTofu, Terragrunt, and provider versions across
> infra templates — editing `versions.tf` and regenerating `.terraform.lock.hcl` via
> `tofu init -upgrade`.

### Adding a new infra template

> **TODO:** Add instructions for creating a new infra template, using `infra/tofu` as the
> reference.
