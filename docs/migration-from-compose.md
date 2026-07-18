# Migration from Compose

Migrate incrementally rather than translating the entire Compose file at once.

## Phase 1

- k3s, Argo CD, cert-manager;
- external GHCR;
- application Helm chart;
- BFFs and game services;
- existing databases remain outside Kubernetes temporarily.

## Phase 2

- VictoriaMetrics and Grafana;
- OpenTelemetry Collector and Tempo;
- ServiceMonitor/VMServiceScrape resources;
- HPA for HTTP/gRPC services.

## Phase 3

- PostgreSQL, Redis, ClickHouse and MinIO;
- CronJobs for backups;
- SOPS-encrypted secrets;
- restore tests.

## Development modes

Keep a small local Compose file only for infrastructure when debugging a single
.NET process from Rider. Use k3d with the same Helm chart for complete integration tests.
