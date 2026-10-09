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

## Integration hold points

No live GitHub delivery, release, image publication, provider sign-in or workspace
builder test is authorised here. P2P helper publication/pin, hardened workspace
builder, registry-client integration and authorised live Helm/GitHub stage evidence
remain separate gates regardless of local fixture results.
