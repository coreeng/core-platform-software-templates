# {{ name }}

Shared monitoring stack generated from the Core Platform `monitoring-stack` software template.

This repository deploys the `core-platform-assets/core-platform-monitoring` Helm chart for a delivery unit.

## Tech Stack

- Prometheus for metrics collection.
- Grafana for dashboards.
- Alertmanager for alert routing.
- Helm values in `p2p/config/` for environment-specific configuration.

## Monitored Delivery Units

The generated values monitor this delivery unit by default:

- non-production stages: `{{ name }}-integration`
- production: `{{ name }}-prod`
- target instance: `{{ name }}`

To monitor additional delivery units, edit the environment values files and add each delivery unit namespace under `prometheus.targetNamespaces` and instance name under `prometheus.targetInstances`.

For integration, update `p2p/config/integration.yaml`:

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

For production, update `p2p/config/prod.yaml`:

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

## Slack Alerting

Slack settings are regular Helm values in the generated repository. To set the Slack channel, add `alertmanager.slack.channel` to the relevant environment values file:

```yaml
alertmanager:
  slack:
    channel: "#team-alerts"
    webhookSecretName: alertmanager-slack-webhook
    webhookSecretKey: url
```

The secret named by `webhookSecretName` must exist in the monitoring namespace and contain the key named by `webhookSecretKey`. The template does not create Slack webhook secrets.

`AGENTS.md` contains generated-repository guidance for coding agents.
