# Notes proof template verification record

## Baseline and scope

- Base: `e2496d91ff2f8c4c6997bc7cde561059bc2e5fdd` (refreshed `origin/main`).
- Branch: `feature/proof-nextjs-java` in `.worktrees/proof-nextjs-java`.
- Baseline `make templates-validate`: exit 0, existing template schema, lint,
  documentation, ingress, numeric USER, security ignore, Java and Next.js checks.
- Shared root target/documentation patch: independent review found no important
  issues. Three targets are additive; existing template behavior is unchanged.
- Initial new `make test-nextjs-java-render`: exit 2 because the application test
  script was not present yet. Application-specific TDD evidence is recorded below
  when that implementation is verified.

## Observed local tooling

- Docker client 29.8.2, daemon 24.0.9, Colima context, native Linux arm64 daemon.
- `docker buildx version`: unavailable in the current client configuration.
- Helm `v4.2.3+g43e8b7f`.
- No daemon configuration or provider authentication changed for this slice.

## Acceptance evidence to record

Coordinator checks before implementation review:

- `make test-nextjs-java-render`: exit 0, strict rendering/Helm contracts for three
  application names.
- `make templates-validate`: exit 0, all existing checks plus the new render gate.
- `make test-nextjs-java-build`: exit 0, five ordinary Docker images exported on
  arm64. Dependency-install, unit-test and application-build layers were cached on
  this repeat run; it is build-output verification, not fresh unit-test execution.
  The runner checksum-verified buildx `v0.38.0` into an ephemeral auth-free Docker
  config. No host plugin installation or daemon change was made.
- `make test-nextjs-java-functional`: exit 0 on the coordinator repeat run. Real
  Chromium/browser/API checks passed for functional, integration and extended
  records. Functional preserved its notes across stopping and restarting frontend,
  backend and PostgreSQL, then verified and removed them. SQL confirmed zero rows
  in the owned disposable database after all tests. Image build layers were cached.
- Post-run Docker container, network and image listings filtered by the proof
  ownership label returned no resources. This is successful-run cleanup evidence;
  failure/cancellation contracts still require implementation review.

Render, ordinary Docker build, and browser/database verification must be reported
separately. A passing Docker suite is not a live Helm/PVC or workspace proof.

- Immutable frontend/browser lockfile installs, actual unit tests, all application
  and stage test image builds, exact platform and any temporary build-client setup.
- Multi-name Jinja/Helm rendering, caller namespace, scoped Secret, exact chart/image
  inventory, all stage Jobs, disabled preview ingress/HPA, no destructive teardown.
- Create/list/reload, rejected invalid text including Unicode boundaries, persistence
  after application/database restart where covered, and exact test-owned cleanup.
- Disposable runner failure/timeout/interruption tests, immutable-ID ownership checks,
  cleanup results and no broad prune, unowned volume deletion or host credential mount.
- Independent implementation spec review, then code-quality/security review and
  fresh post-remediation checks before the local commit.

## Implementation review remediation

Independent spec review requested the missing pinned Gradle wrapper and robust
disposable-runner cleanup under interruption/build timeout, with offline injected
failure coverage. Successful-run Docker evidence above does not establish these
contracts. Remediation is required before final review/commit. The separately
coordinated root patch adds `test-nextjs-java-runner` to the render gate.

Remediation coordinator checks:

- `make templates-validate`: exit 0, all existing template gates, strict rendering
  for three names, actual sibling P2P helper stage contracts and 22 offline runner
  tests. Machine-specific fixture defaults have been removed; helper-stage checks
  identify the selected real local fixture separately from pure Helm rendering.
- The implementation owner reports copying all four checksum-pinned Gradle 9.8
  wrapper files, building through `./gradlew`, signal/process-group handling,
  reserved-resource recovery and independent cleanup. These changes await spec
  re-review and independent code-quality review before acceptance.

- Spec re-review approved the isolated stream: both Important findings resolved;
  reviewer reran the render gate including actual local-helper contracts and all
  22 runner tests. No remaining Important/Critical spec gaps were reported.
- Coordinator `make test-nextjs-java-build` after remediation: exit 0, five images
  exported. Fresh nonce-invalidated frontend lint/test/production-build step ran
  all three Jest suites (4/4 tests); Gradle wrapper `build --rerun-tasks` ran backend
  tests (4 run, 4 passed, 0 failed, 0 skipped). Dependency installation layers were
  cached; unit-test steps were not cached. The Gradle build reports deprecations
  for Gradle 10; it passes on the pinned Gradle 9.8 distribution.

- Coordinator post-remediation `make test-nextjs-java-functional`: exit 0, fresh
  frontend 4/4 and backend 4/4 unit tests, five ordinary image builds, functional
  create/list/refresh/reload and validation checks, preserved-record verification
  after stopping/restarting both application containers and PostgreSQL, then real
  integration and extended checks. The disposable database had zero remaining
  notes after the suites.
- Post-remediation filtered Docker container/network/volume/image inventories were
  empty for the proof ownership label. `git diff --check` passed.

The subsequent review and final verification outcome is recorded below; the
preceding checkpoint did not authorise an implementation commit.

Code-quality review requested a CI compatibility fix: general template validation
cannot depend on an unpublished sibling fixture absent from the existing checkout
workflow. Coordinator reproduced failure with an explicitly unavailable fixture
(exit 2). Shared target wiring now separates `test-nextjs-java-structure` for CI
from fixture-required `test-nextjs-java-render` for local P2P qualification. The
review also found stderr loss in container diagnostics; regression remediation is
in progress. Earlier passing local checks are not evidence that CI was compatible.

## Final acceptance for independent application slice

- Final code-quality re-review approved local commitment with no remaining
  Important/Critical findings. Container-log diagnostics retain both streams without
  contaminating ID/JSON parsing; four new regressions bring the offline suite to 26.
- Clean coordinator `P2P_HELPER_DIR=/nonexistent-nextjs-java-fixture make
  templates-validate`: exit 0, all existing checks, three-name structural rendering,
  explicit P2P UNQUALIFIED message and 26 passing offline tests. This proves that
  general validation does not require the unpublished sibling fixture; it is not a
  live GitHub Actions run.
- Clean coordinator `make test-nextjs-java-render`: exit 0, three-name rendering,
  actual local P2P helper stage contracts and 26 passing offline tests. The full
  gate still fails if its required helper fixture is unavailable.
- Clean coordinator `make test-nextjs-java-functional`: exit 0 after final review
  fixes, fresh frontend 4/4 and backend 4/4 unit tests, all five ordinary image
  builds, real functional/integration/extended browser/API checks and full
  application/PostgreSQL restart persistence. Database assertions confirmed no
  remaining test notes. Dependency-install layers used Docker cache; unit-test
  steps reran. No workspace builder, registry writes or live Helm stage used.
- Scope is reviewed and verified for local commitment only. General validation and
  full fixture qualification remain separate targets. Branch/worktree are retained;
  no push, PR, release, provider login or live GitHub delivery is authorised.
- Final filtered Docker container/network/volume/image inventories were empty.
  Staging exposed Git's default CRLF whitespace warning on the byte-identical
  upstream Windows Gradle wrapper. Its existing repository convention was preserved;
  `git -c core.whitespace=cr-at-eol diff --cached --check` passed without rewriting
  the wrapper or changing persistent Git configuration.
- Application and owned tests committed locally as `c1ddaf6` on the verified feature
  branch. Shared validation-target wiring and documentation are committed separately.

## Integration hold points

No live GitHub delivery, release, image publication, provider sign-in or workspace
builder test is authorised here. P2P helper publication/pin, hardened workspace
builder, registry-client integration and authorised live Helm/GitHub stage evidence
remain separate gates regardless of local fixture results.
