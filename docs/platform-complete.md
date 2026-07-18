# Platform completion

This patch completes the non-secret platform layer:

- cert-manager and Let's Encrypt ClusterIssuer bootstrap;
- KEDA operator;
- VictoriaMetrics, VMAlert, Alertmanager and Grafana;
- VictoriaMetrics dashboards and PostgreSQL/Redis exporters;
- monolithic Tempo with a PVC;
- OpenTelemetry Collector;
- local Vault and External Secrets Operator bootstrap;
- frontend Deployment, Service and Ingress;
- HPA for selected HTTP/gRPC services and all game workers;
- baseline ingress NetworkPolicies;
- CI rendering and plaintext-secret guard.

## Values still required

Replace every `CHANGE_ME`:

- production domain names;
- Let's Encrypt account email;
- GHCR image tags or immutable digests;
- Grafana host;
- actual application configuration that is secret.

## KEDA

KEDA is installed, but no `ScaledObject` is enabled yet. A correct trigger requires
a real queue or exported metric. CPU-based scaling remains on HPA. Add KEDA only
for a durable backlog metric such as Redis Streams pending entries, a queue length,
or a VictoriaMetrics query that directly represents waiting work.

## Tempo choice

Tempo runs in monolithic mode because this is a single-node VPS. It is not exposed
through Ingress. Grafana accesses it through the cluster Service.

## Before first reconciliation

1. Replace `CHANGE_ME` values.
2. Run GitHub Actions successfully.
3. Add encrypted secrets.
4. Bootstrap Argo CD.
5. Verify certificates, PVCs, scrape targets and backup Jobs.
