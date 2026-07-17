# Production readiness checklist

## Static validation

- [ ] `go-task clean`
- [ ] `go-task validate`
- [ ] `go-task placeholders` returns no unresolved production values
- [ ] GitHub Actions validation passes
- [ ] working tree is clean
- [ ] all application images exist
- [ ] all production images use immutable tags or digests

## Host and networking

- [ ] Ansible inventory contains the correct VPS
- [ ] SSH access works
- [ ] ports 22, 80 and 443 are reachable
- [ ] database ports are not public
- [ ] DNS records resolve to the VPS
- [ ] k3s node reports `Ready`

## GitOps

- [ ] Flux is bootstrapped
- [ ] Flux source is ready
- [ ] all Kustomizations are ready
- [ ] all HelmReleases are ready
- [ ] no repeated reconciliation errors exist

## Security

- [ ] no plaintext secrets exist in Git
- [ ] age private key is backed up separately
- [ ] GitHub tokens are scoped and rotated
- [ ] Grafana access is protected
- [ ] Admin BFF access is protected
- [ ] MinIO console is not public
- [ ] Pod Security warnings have been reviewed

## Stateful services

- [ ] PostgreSQL is ready
- [ ] Redis is ready
- [ ] ClickHouse is ready
- [ ] MinIO is ready
- [ ] all PVCs are bound
- [ ] disk capacity is sufficient
- [ ] application migrations are complete

## Backups

- [ ] all local backup CronJobs are enabled
- [ ] manual PostgreSQL backup succeeds
- [ ] manual Redis backup succeeds
- [ ] manual ClickHouse backup succeeds
- [ ] manual MinIO backup succeeds
- [ ] off-site synchronization succeeds
- [ ] PostgreSQL restore has been tested
- [ ] ClickHouse restore has been tested
- [ ] backup alerts are visible in VictoriaMetrics

## Application

- [ ] frontend is reachable
- [ ] Telegram endpoint is reachable
- [ ] REST API readiness endpoint succeeds
- [ ] Admin BFF readiness endpoint succeeds
- [ ] identity communication succeeds
- [ ] wallet communication succeeds
- [ ] all game workers are ready
- [ ] HPA reports valid CPU metrics

## Observability

- [ ] Grafana is reachable
- [ ] VictoriaMetrics receives node metrics
- [ ] VictoriaMetrics receives application metrics
- [ ] Tempo receives application traces
- [ ] VMRule resources are accepted
- [ ] Alertmanager has a real notification receiver
- [ ] a test alert has been delivered

## Final verification

```bash
./scripts/preflight.sh
./scripts/post-deploy-check.sh
./scripts/manual-backup.sh
./scripts/cluster-status.sh
```
