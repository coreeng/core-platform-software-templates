# {{ name }}

Shared Core Platform monitoring stack.

This repository is generated from the `monitoring-stack` software template. It deploys the
`core-platform-assets/core-platform-monitoring` Helm chart through the standard P2P stages.

## Deployment

Use the generated P2P targets:

```bash
make p2p-functional
make p2p-nft
make p2p-integration
make p2p-extended-test
make p2p-prod
```

## Monitoring Targets

This template does not define custom software-template parameters. The generated Helm values target
the monitoring delivery unit itself:

- non-production stages: `{{ name }}-integration`
- production: `{{ name }}-prod`
- target instance: `{{ name }}`

If additional monitoring targets are needed later, add them in the generated repository values files
after rendering the template. This infra template does not add dashboard or template-rendering
behavior.

To monitor additional delivery units, edit each environment values file and add the delivery unit's
namespace and instance. For example, to monitor `payments-api` and `orders-api` in integration,
update `p2p/config/integration.yaml`:

```yaml
prometheus:
  targetNamespaces:
    - {{ name }}-integration
    - payments-api-integration
    - orders-api-integration
  targetInstances:
    - {{ name }}
    - payments-api
    - orders-api
```

For production, update `p2p/config/prod.yaml` with production namespaces:

```yaml
prometheus:
  targetNamespaces:
    - {{ name }}-prod
    - payments-api-prod
    - orders-api-prod
  targetInstances:
    - {{ name }}
    - payments-api
    - orders-api
```

## Description

The generated `app.yaml` contains the repository description:

```yaml
description: Shared Core Platform monitoring stack
```

Change that value in the generated repository if a team-specific description is needed.

## Slack Alerting

Slack settings are regular Helm values in the generated repository. To set the Slack channel, add
`alertmanager.slack.channel` to the relevant environment values file. For example:

```yaml
alertmanager:
  slack:
    channel: "#team-alerts"
    webhookSecretName: alertmanager-slack-webhook
    webhookSecretKey: url
```

The secret named by `webhookSecretName` must exist in the monitoring namespace and contain the key
named by `webhookSecretKey`. The template does not create Slack webhook secrets.

## P2P Validation

The P2P functional, NFT, integration, and extended-test stages deploy this monitoring chart and then
run `helm test` if the chart defines Helm test hooks. If the chart has no test hooks, the stage treats
successful deployment as deploy-only validation.
