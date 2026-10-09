# {{ name }} — notes proof

Next.js/React/TypeScript serves the notes UI on `3000`. `/api/notes` proxies
server-side to Java on `8080`, without exposing database credentials to the browser
or frontend process. Spring Boot uses JDBC and Flyway against PostgreSQL. Notes
are 1–200 Unicode codepoints (not UTF-16 units); SQL enforces the same length.
Null characters are rejected because PostgreSQL text does not support them.

The frontend exposes `/readyz`, `/livez` on `3000` and `/metrics` on `8081`.
The backend exposes `/health` and `/prometheus` on `8081`. Operational ports and
the backend have no ingress. The chart uses one replica per component, disabled
ingress/HPA/VPA, and a PostgreSQL StatefulSet with a retained `1Gi` PVC. No stage
scales down or destroys applications/database/PVCs after testing.

## Deploy into an already supplied namespace

Provision the application-specific `{{ name }}-database` Secret in every target
namespace with `username` and `password` keys through your approved secret manager.
Do not commit credentials. Only backend and PostgreSQL reference that Secret;
the test Jobs also have no database credentials. The database is named `notes`.
This is a disposable proof, not a production database backup/security design.

```sh
export P2P_HELPER_DIR=/absolute/path/to/reviewed/local-p2p-fixture
make p2p-images
make p2p-build
make p2p-functional P2P_NAMESPACE_FUNCTIONAL=your-supplied-namespace
```

The helper is intentionally local and required: no unreleased revision is downloaded
or represented as a release. Existing helper defaults govern namespaces, versions
and registries. `P2P_IMAGE_NAMES` lists both deployable images for promotion;
test images use the helper's functional/integration/extended suffix contract.
Integration and extended stages execute the same real browser/API suite with
stage-specific UUID records. Prod deploys both promoted applications. NFT fails
explicitly as unsupported. `helm test --logs --timeout 5m` waits for the Job without
tearing down the application or database. Test cleanup deletes only the exact UUID
and text created by that run through the internal backend cleanup endpoint.

Build application images directly from `frontend/` and `backend/`; both Dockerfiles
execute unit tests. The backend contains the checksum-pinned Gradle 9.8 wrapper
and builds through `./gradlew` on JDK 26. Supply a fresh
`--build-arg UNIT_TEST_NONCE=<unique-value>` for fresh unit-test execution without
discarding cached dependency installs. The parent repository's canonical Docker
runner always supplies this argument and logs fresh unit counts.
Build the browser image from `p2p/tests/`. Native Helm templates
are raw-wrapped for the legacy template renderer; remove raw delimiters only through
template instantiation, not manual Helm installation of the unrendered skeleton.

Live GitHub workflow qualification, helper publication, and workspace BuildKit
qualification require separate approval. No automatic delivery workflows are
installed while this proof requires the unpublished local fixture.

The parent software-template repository separates fixture-free structural/offline
validation (`make templates-validate` / `make test-nextjs-java-structure`) from
full local helper stage qualification (`make test-nextjs-java-render` with the
actual reviewed `P2P_HELPER_DIR`). Structural success alone does not qualify P2P
stage contracts or a helper release.
