# Next steps after patch 2

## Correctness fixes included

- Keep k3s ServiceLB enabled so packaged Traefik can expose ports 80/443.
- Use separate images for identity, wallet and each BFF.
- Reuse one backend image only for `game-*` deployments.
- Use separate PostgreSQL connection-string secret keys per bounded context.
- Add startup probes.
- Add a GitHub Actions validation workflow.
- Keep secrets outside Helm values and prepare them for SOPS encryption.

## Still intentionally incomplete

- Exact GHCR image names and immutable digests.
- Real domains and ACME email.
- PostgreSQL/Redis/ClickHouse/MinIO charts and backup jobs.
- Tempo and OpenTelemetry Collector.
- SOPS age public key and encrypted Secret.
- Per-service environment variables from the current Compose file.
- Frontend Deployment and image.
- KEDA custom metrics.

Do not run `flux bootstrap` against production until every `CHANGE_ME` is reviewed.
