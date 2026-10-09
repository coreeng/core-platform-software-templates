# Proof notes template implementation plan

> **For agentic workers:** Use `subagent-driven-development` or `executing-plans`.

**Goal:** Deliver the independently verifiable application slice of Task 9.

**Architecture:** One generated application has Next.js, Java and PostgreSQL in a
namespace-supplied umbrella Helm release. Ordinary Docker tests are separate from
blocked workspace builder proofs.

**Tech Stack:** Next.js/React/TypeScript, Spring Boot/JDBC/Flyway, PostgreSQL,
Helm, Playwright, existing Gradle wrapper and Yarn conventions.

## 1. Establish failing application contracts

- [ ] Add `tests/nextjs_java_template_test.sh` and render helper
  `tests/render_nextjs_java.py` before creating the template.
- [ ] Run `bash tests/nextjs_java_template_test.sh`; require failure for the missing
  template rather than a broken test environment.
- [ ] Cover valid rendered names, canonical lockfiles, application image inventory,
  stage test images, caller namespaces, credential scoping and Helm/Jinja escaping.

## 2. Implement the generated application

- [ ] Create `nextjs-java/web/template.yaml` with the current metadata/schema shape.
- [ ] Create `skeleton/frontend/` with a notes form/list, same-origin API proxy,
  runtime probes/metrics, unit tests, canonical lockfile and Dockerfile.
- [ ] Create `skeleton/backend/` with copied pinned Gradle wrapper, Java API,
  validation, JDBC repository, Flyway migration, unit tests and Dockerfile.
- [ ] Test empty/null, 1/200/201-character bodies and Unicode length equivalence;
  ensure invalid input cannot reach persistence and backend errors fail requests.

## 3. Implement release and ordinary P2P targets

- [ ] Create `skeleton/p2p/chart/` with exact-version frontend/backend dependencies,
  PostgreSQL PVC/workload, scoped Secret and real browser-test Helm Jobs.
- [ ] Create stage values and Make build/deploy/test targets; preserve ordinary CI
  namespace/version bindings and use only an explicit local portability fixture.
- [ ] List frontend/backend in `P2P_IMAGE_NAMES`; stage suffixes keep ephemeral test
  images outside production promotion. Functional verification must not scale down
  the application or delete PostgreSQL/PVCs. NFT must not report synthetic success.

## 4. Add owned local verification and coordinate shared targets

- [ ] Create `tests/nextjs_java_local.py` for normal Docker build/functional modes,
  unique labelled owned resources, bounded commands and cleanup on failures.
- [ ] Coordinate only these additive root targets, without changing existing ones:

  ```make
  test-nextjs-java-render:
  	bash tests/nextjs_java_template_test.sh
  test-nextjs-java-build:
  	python3 tests/nextjs_java_local.py build
  test-nextjs-java-functional:
  	python3 tests/nextjs_java_local.py functional
  ```

- [ ] Add the render check to `templates-validate` and update root layout/pin guidance
  serially. Run `make templates-validate` and all three new targets.
- [ ] Functional verification creates/lists/reloads notes, rejects invalid bodies,
  proves restart persistence and removes only test-owned note IDs.

## 5. Review, verify and commit locally

- [ ] Independent spec review, then code-quality/security review; fix findings and
  re-review. Record precise checks and any unverified gates.
- [ ] Re-run affected canonical checks and `git diff --check` after remediation.
- [ ] Confirm branch is `feature/proof-nextjs-java`, then commit scoped files locally
  with a standalone description. Do not push, publish or open a PR.
