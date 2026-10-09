# {{ name }} engineering guide

This isolated proof contains `frontend/` (Next.js React TypeScript), `backend/`
(Spring Boot Java JDBC Flyway), and `p2p/chart/` (aliased frontend/backend app charts
plus PostgreSQL StatefulSet/PVC). Keep ports, probes and Secret scoping aligned.

The frontend proxies `/api/notes` to internal `/notes`; never add database credentials
or `NEXT_PUBLIC_*` backend/Secret settings to it. Validate text using Unicode
codepoints in both runtimes and retain the PostgreSQL length check. Do not add
bulk record cleanup: browser tests own stage-specific UUID/text pairs only.

Build/run via the reviewed explicit `P2P_HELPER_DIR` fixture. Do not invent a helper
release, download unpublished revisions, add passing placeholder tests, or claim
workspace compatibility. Both frontend/backend are deployable promotion images;
functional/integration/extended images run the real browser/API runner. NFT is
unsupported. Stages require an existing namespace and its app-specific database
Secret. Do not create namespaces implicitly, scale down post-test, delete the PVC,
mount host Docker sockets/credentials, or enable automatic GitHub delivery yet.

Keep published chart/image pins and canonical Yarn locks checked in. Unit tests
run in ordinary Docker builds; the parent template repository supplies isolated
Docker orchestration for database/application restart persistence verification.
