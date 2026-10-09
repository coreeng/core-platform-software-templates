# Database-backed notes proof template

## Scope and authority

Implement the approved independent application slice of Task 9, not local workspace
delivery. All authored changes belong to `core-platform-software-templates` on
`feature/proof-nextjs-java`, based on refreshed `origin/main`. No publication,
provider login, live GitHub stages or workspace security changes are authorised.
Reviewed and verified changes may be committed locally; pushing branches, opening
PRs and publishing images or releases require separate permission.

## Journey and interface

A platform builder currently has separate Java and Next.js examples but no single
generated application exercising browser-to-backend persistence. The new
`nextjs-java-web` template generates one application with a notes form and list.
Creating a valid note, reloading the browser and restarting application containers
must retain the note in PostgreSQL. This is a generated-repository interface, not
a Portal or CLI feature.

## Architecture

Next.js proxies same-origin `/api/notes` requests to Java's internal `/notes` API.
Java validates text length from 1 through 200 Unicode code points and persists UUID,
body and creation timestamp through JDBC and Flyway. PostgreSQL's CHECK constraint
enforces the same range. Database credentials reach only PostgreSQL and the backend
through an application-specific Secret. The frontend receives no database secret.

A caller supplies the namespace for one umbrella Helm release with exact-version
`core-platform-app` frontend/backend dependencies and a pinned PostgreSQL workload
with PVC. Default ingress is disabled. Application probes and metrics follow the
existing framework templates. Preview values use one replica without HPA or
post-test application scale-down. Refresh never drops the database or PVC.

## Build and test contracts

The deployable application image inventory contains frontend and backend images;
browser-test stage images are separate and must not enter production promotion.
Functional, integration and extended checks perform real database-backed browser
and API assertions and clean up only IDs created by that test invocation. Tests
must fail on service, validation or persistence failures. NFT is not qualified.

Use the locally reviewed P2P portability fixture through an explicit caller path.
No released helper pin exists yet; an absent fixture fails clearly instead of
silently downloading an invented revision. Keep ordinary CI stage namespace and
version behavior. Do not claim released-template or workspace compatibility.

## Verification and ownership

Owned disposable Docker orchestration proves normal image builds, immutable Yarn
installs, application unit tests, browser/API behavior and restart persistence.
Render checks cover multiple application names, Helm/Jinja boundaries, namespaces,
secret scoping, pinned dependencies and full image inventory. Offline orchestration
tests cover cleanup and failure behavior where applicable. No Compose,
Testcontainers or workspace Docker socket is introduced into generated dependencies.

Implementation owns `nextjs-java/` and its `tests/` files. Root Makefile target
wiring and root documentation are a separate, serial coordination patch. Existing
templates are not migrated. Read-only consumers are P2P and Core Platform Assets;
the future preview executor is an integration consumer, not delivered here.

## Remaining integration gates

Reviewed P2P helper release and consuming pin; qualified hardened workspace builder;
registry credential/transport integration; namespace/PVC/Helm qualification on the
approved workspace sandbox; authorised disposable GitHub Fast Feedback, Extended
Test and Prod runs. None is established by Docker or render fixture success.
