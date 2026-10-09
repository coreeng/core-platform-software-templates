# Core Platform Software Templates

Software templates to be used by users of Core Platform for quick bootstrap of new applications.

The [corectl](https://github.com/coreeng/corectl) CLI tool should be used for working with templates (exploring, rendering, and creating applications from templates).

## Notes proof application

`nextjs-java/web` generates a Next.js frontend, Java backend and PostgreSQL notes
application as one Helm release. It is an independently tested proof template,
not a claim of supported local workspace delivery. See
[`nextjs-java/web/README.md`](nextjs-java/web/README.md) for its dependency inventory
and explicit local P2P helper-fixture requirement.

Canonical local verification:

```sh
make templates-validate
make test-nextjs-java-structure
make test-nextjs-java-render
make test-nextjs-java-runner
make test-nextjs-java-build
make test-nextjs-java-functional
```

The build and functional targets use ordinary Docker and owned disposable test
resources, not the workspace builder. They do not run live GitHub stages or publish
images. Workspace builder/registry qualification, a released P2P helper pin and
authorised disposable GitHub delivery runs remain separate integration gates.

General `templates-validate` includes structural rendering and offline runner tests
without requiring an unpublished helper. It explicitly leaves P2P stage contracts
unqualified. `test-nextjs-java-render` is the separate full local qualification gate:
supply `P2P_HELPER_DIR` pointing to the reviewed portability fixture (or use its
standard sibling worktree layout). A missing/incomplete fixture fails that gate.
