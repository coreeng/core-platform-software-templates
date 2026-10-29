# Showcase template contract and implementation plan

The Docker, Go, Java, Next.js, Python and Nextra web templates support early
browser access after a successful FF build. Their manual workflow dispatch has
an optional boolean `showcase` input, default false. Only an explicitly enabled
dispatch forwards true to the reusable FF workflow; pushes and PRs remain false.

Each template implements `p2p-showcase: deploy-showcase` and a Showcase values
file, inheriting the standard application configuration. The existing Helm
recipe deploys the built application version from the FF registry into a
separate persistent Showcase namespace. It neither rebuilds nor runs integration
tests. Ingress disablement remains honored. Existing repositories are unchanged.

Implementation sequence:

1. Declare and forward the input in all six generated FF workflows.
2. Add the deploy-only Make target and stage configuration.
3. Document the environment in generated agent guidance.
4. Validate template definitions, Showcase contracts, existing template checks
   and Node runtime containers.

For integration testing, all generated P2P workflow references and Makefile
downloads use the `coreeng/p2p` branch `codex/showcase` from PR #195. They must
move back to the compatible P2P v1 release before general adoption. Managed
Portal/corectl support is also required.
The native new-app wizard enables Showcase automatically with no user toggle;
other workflow callers retain the default-false contract. Showcase failure fails
FF; the normal pipeline's tests and promotion dependencies are unchanged.
