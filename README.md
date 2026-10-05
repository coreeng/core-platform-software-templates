# Core Platform Software Templates

Software templates to be used by users of Core Platform for quick bootstrap of new applications.

The [corectl](https://github.com/coreeng/corectl) CLI tool should be used for working with templates (exploring, rendering, and creating applications from templates).

## Application ingress

Web templates preserve `config.ingress.enabled` from `app.yaml` and consume
`P2P_INGRESS_DOMAIN` and `P2P_INGRESS_CLASS` prepared for the actual deployment
cluster. An authorized cluster without a profile supplies empty domain/class;
the toggle remains unchanged and deployment continues. Application chart 0.17.1
or later skips unusable Ingress resources without a domain while retaining the
application and Service. Templates use the latest stable published chart.
Configure the profile and deploy again to enable ingress. All automated tests,
including performance tests, always use Services independently of browser ingress.
