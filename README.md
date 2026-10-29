# Core Platform Software Templates

Software templates to be used by users of Core Platform for quick bootstrap of new applications.

The [corectl](https://github.com/coreeng/corectl) CLI tool should be used for working with templates (exploring, rendering, and creating applications from templates).

## Showcase

The six web application templates accept a boolean `showcase` input on their
Fast Feedback manual dispatch. It defaults to false. A flagged main-branch run
deploys the successfully built application version to a persistent Showcase
environment on the Fast Feedback cluster, independently of the remaining tests.
The native new-app wizard enables it automatically; existing generated repositories
are unchanged. Deployments use `p2p-showcase: deploy-showcase` and
`p2p/config/showcase.yaml`, without rebuilding or running integration tests.

Publish compatible Portal/corectl support and the P2P `v1` Showcase workflow
contract before adopting these generated workflows.
