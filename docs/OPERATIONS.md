# CasinoShiz Infrastructure Operations Guide

## Status

The repository contains the non-secret infrastructure required to deploy
CasinoShiz onto a single-node k3s cluster.

Implemented:

- host bootstrap with Ansible;
- single-node k3s;
- Flux-compatible GitOps repository structure;
- Traefik ingress supplied by k3s;
- cert-manager and Let's Encrypt ClusterIssuer bootstrap;
- application Helm chart;
- frontend, BFF, identity, wallet and game workloads;
- CPU-based Horizontal Pod Autoscaling;
- KEDA operator for future queue/backlog-based scaling;
- PostgreSQL, Redis, ClickHouse and MinIO StatefulSets;
- local scheduled backups;
- optional off-site backup synchronization;
- VictoriaMetrics, VMAlert, Alertmanager and Grafana;
- OpenTelemetry Collector and Tempo;
- baseline NetworkPolicy resources;
- Taskfile-based validation;
- GitHub Actions validation.

Still required before production:

- replace all `CHANGE_ME` values;
- configure real GHCR image names and immutable tags/digests;
- configure real DNS records;
- configure the Let's Encrypt account email;
- create and encrypt Kubernetes secrets using SOPS and age;
- enable and configure off-site backup synchronization;
- perform a tested restore;
- run a final successful `go-task validate`.

The infrastructure is designed for a single VPS. It is not highly available.

---

## Architecture

```text
Internet
   |
   v
Traefik ingress
   |
   +--> frontend
   +--> telegram-bff
   +--> admin-bff
   +--> rest-api
            |
            +--> identity
            +--> wallet
            +--> game-* workers
            |
            +--> PostgreSQL
            +--> Redis
            +--> ClickHouse
            +--> MinIO

Applications
   |
   +--> OpenTelemetry Collector --> Tempo
   |
   +--> /metrics --> VictoriaMetrics --> Grafana
```

Infrastructure ownership is split as follows:

- **Ansible** owns the operating system and k3s installation.
- **Flux** owns Kubernetes resources.
- **Helm** renders CasinoShiz application workloads.
- **Kustomize** composes the production cluster tree.
- **SOPS + age** will own encrypted secrets.
- **Taskfile** provides local and CI validation commands.

---

## Repository layout

```text
ansible/
  inventory/
  playbooks/
  roles/

charts/
  casinoshiz/

clusters/
  production/

data/
  backup-storage/
  postgres/
  redis/
  clickhouse/
  minio/

platform/
  namespaces/
  cert-manager/
  keda/
  monitoring/
  tracing/
  network-policies/

docs/
Taskfile.yml
.sops.yaml
```

### Important paths

| Path | Purpose |
|---|---|
| `ansible/playbooks/site.yml` | Prepare the VPS and install k3s |
| `clusters/production/kustomization.yaml` | Production Flux entrypoint |
| `charts/casinoshiz/values-production.yaml` | Production application values |
| `clusters/production/casinoshiz/values-configmap.yaml` | Values consumed by Flux HelmRelease |
| `data/data.secret.yaml.example` | Data secret example |
| `clusters/production/casinoshiz/casinoshiz.secret.yaml.example` | Application secret example |
| `platform/monitoring/helmrelease.yaml` | VictoriaMetrics and Grafana |
| `platform/tracing/` | OpenTelemetry Collector and Tempo |
| `Taskfile.yml` | Validation and rendering commands |

---

## Required local tools

On Arch Linux or CachyOS:

```bash
sudo pacman -S \
  ansible \
  helm \
  kustomize \
  go-task \
  kubectl
```

Flux, SOPS and age are required for the final deployment stage:

```bash
sudo pacman -S sops age
```

Install the Flux CLI using its official installation method or an appropriate
distribution package.

Verify tools:

```bash
go-task tools
```

---

## Validation

Run validation from the repository root:

```bash
go-task clean
go-task validate
```

This performs:

1. `helm lint`;
2. application Helm rendering;
3. full production Kustomize rendering;
4. basic plaintext-secret detection.

Rendered manifests are written to:

```text
.task/rendered/casinoshiz.yaml
.task/rendered/production.yaml
```

Useful commands:

```bash
go-task --list
go-task lint
go-task render:chart
go-task render:cluster
go-task ansible:check
go-task secrets:check
go-task placeholders
go-task validate
```

Before deployment, the following command should return no unresolved production
placeholders:

```bash
go-task placeholders
```

---

## Production values

Replace every `CHANGE_ME` in the repository.

Typical locations:

```text
ansible/inventory/hosts.yml
charts/casinoshiz/values-production.yaml
clusters/production/casinoshiz/values-configmap.yaml
platform/cert-manager/clusterissuer-job.yaml
platform/monitoring/helmrelease.yaml
.sops.yaml
```

Required values include:

- VPS IP address;
- public frontend domain;
- Telegram BFF domain;
- Admin BFF domain;
- REST API domain;
- Grafana domain;
- ACME account email;
- GHCR image repositories;
- immutable image tags or digests.

Prefer immutable image digests:

```yaml
image:
  repository: casinoshiz-rest-api
  tag: sha-0123456789abcdef
```

Do not deploy mutable `latest` tags to production.

---

## DNS

Create DNS records pointing to the VPS public IP:

```text
app.example.com       -> VPS IP
tg.example.com        -> VPS IP
admin.example.com     -> VPS IP
api.example.com       -> VPS IP
grafana.example.com   -> VPS IP
```

Ports required externally:

```text
22/tcp   SSH
80/tcp   HTTP and ACME challenge
443/tcp  HTTPS
```

Do not expose PostgreSQL, Redis, ClickHouse, MinIO API, Tempo or the
OpenTelemetry Collector directly to the Internet.

---

## Host bootstrap

Edit:

```text
ansible/inventory/hosts.yml
```

Example:

```yaml
all:
  hosts:
    production:
      ansible_host: 203.0.113.10
      ansible_user: root
      ansible_port: 22
```

Validate Ansible:

```bash
go-task ansible:check
```

Run bootstrap:

```bash
cd ansible
ansible-playbook playbooks/site.yml
```

The playbook:

- installs required operating-system packages;
- enables IPv4 forwarding;
- creates `/srv/casinoshiz`;
- installs k3s;
- waits for the Kubernetes API;
- writes a local ignored `kubeconfig`.

Use the generated kubeconfig:

```bash
export KUBECONFIG="$PWD/../kubeconfig"
kubectl get nodes
```

Expected result:

```text
NAME       STATUS   ROLES                  AGE   VERSION
server     Ready    control-plane,master   ...   ...
```

---

## Flux bootstrap

Flux should reconcile:

```text
clusters/production
```

Example bootstrap:

```bash
export GITHUB_TOKEN=...

flux bootstrap github \
  --owner=cpp20120 \
  --repository=CasinoShiz.Infrastructure \
  --branch=main \
  --path=clusters/production \
  --personal
```

After bootstrap:

```bash
flux get all -A
kubectl get helmreleases -A
kubectl get kustomizations -A
```

Recommended reconciliation order:

1. namespaces;
2. cert-manager;
3. ClusterIssuer;
4. KEDA;
5. monitoring;
6. tracing;
7. data services;
8. CasinoShiz workloads.

---

## Application workloads

The Helm chart deploys:

- frontend;
- identity service;
- wallet service;
- Telegram BFF;
- Discord BFF;
- Admin BFF;
- REST API;
- one `game-*` Deployment per enabled game module.

The game services use a shared backend image with a different:

```text
Backend__Modules
```

value.

Health endpoints expected by workloads:

```text
/health/live
/health/ready
```

Metrics endpoint expected by VictoriaMetrics:

```text
/metrics
```

If the real applications use different endpoints, update the Helm templates
before deployment.

---

## Autoscaling

CPU-based HPA is enabled for:

- Telegram BFF;
- Discord BFF;
- REST API;
- game workers.

Identity, wallet and admin workloads are not scaled by default.

Default policy:

```text
minimum replicas: 1
maximum replicas: 4
target CPU: 65%
scale-down stabilization: 300 seconds
```

KEDA is installed but no `ScaledObject` is enabled.

Do not invent a KEDA trigger. Add one only when a real backlog metric exists,
for example:

- Redis Streams pending entries;
- durable job queue length;
- effect execution backlog;
- VictoriaMetrics query representing waiting work.

---

## Data services

The single-node cluster runs:

| Service | Storage | Default PVC |
|---|---:|---:|
| PostgreSQL | local-path | 30 GiB |
| Redis | local-path | 10 GiB |
| ClickHouse | local-path | 50 GiB |
| MinIO | local-path | 50 GiB |
| Backup storage | local-path | 50 GiB |

PostgreSQL contains separate databases for:

```text
backend
identity
wallet
```

This is bounded-context separation within one PostgreSQL process, not physical
database-server isolation.

### Single-node limitation

All PVCs are located on the same VPS. StatefulSets provide stable Kubernetes
identity and storage attachment, but not high availability.

A failed VPS or failed disk can destroy both the live data and local backups.

---

## Backup schedule

Times use `Europe/Helsinki`.

| Time | Backup |
|---|---|
| 02:15 | PostgreSQL logical dumps |
| 02:45 | Redis RDB and AOF copy |
| 03:30 | ClickHouse native backup |
| 04:15 | MinIO mirror |
| 05:30 | Optional off-site synchronization |

Local retention:

```text
PostgreSQL: 14 days
Redis:      14 days
ClickHouse: 14 days
MinIO:       7 days
```

Inspect CronJobs:

```bash
kubectl get cronjobs -n data
```

Inspect recent Jobs:

```bash
kubectl get jobs -n data --sort-by=.metadata.creationTimestamp
```

Run a backup manually:

```bash
kubectl create job \
  --from=cronjob/postgres-backup \
  postgres-backup-manual-$(date +%s) \
  -n data
```

Inspect logs:

```bash
kubectl logs -n data job/<job-name>
```

---

## Off-site backups

The off-site synchronization CronJob is initially suspended:

```yaml
spec:
  suspend: true
```

It uses `rclone` and expects the secret:

```text
rclone-config
```

After configuring and encrypting the rclone configuration, enable it:

```bash
kubectl patch cronjob backup-offsite-sync \
  -n data \
  --type merge \
  -p '{"spec":{"suspend":false}}'
```

The production repository should contain this change declaratively rather than
relying permanently on a manual patch.

Off-site storage should be in another failure domain:

- another cloud provider;
- external S3-compatible storage;
- object storage in another region;
- a separately administered backup server.

---

## Restore testing

Backups are not considered valid until restored.

### PostgreSQL

Create an isolated database:

```bash
createdb \
  -h postgres.data.svc.cluster.local \
  -U postgres \
  restored_backend
```

Restore:

```bash
pg_restore \
  -h postgres.data.svc.cluster.local \
  -U postgres \
  --dbname restored_backend \
  /backup/postgres/<timestamp>/backend.dump
```

Validate application migrations and critical queries against the restored
database.

### ClickHouse

Example:

```sql
RESTORE DATABASE cazinoshiz
FROM Disk('backup', '<timestamp>');
```

Restore into an isolated environment before replacing production data.

### Redis

Restore into a temporary Redis workload using the copied RDB/AOF files.
Validate keys, TTLs and stream/queue state before promotion.

### MinIO

Mirror backup data into a temporary MinIO instance or test bucket and verify:

- expected bucket count;
- object count;
- object checksums;
- representative GIF/media downloads.

---

## Monitoring

VictoriaMetrics stack provides:

- VMSingle;
- VMAgent;
- VMAlert;
- Alertmanager;
- Grafana;
- Kubernetes scraping.

Grafana is exposed through Traefik.

Tempo is not exposed publicly. Grafana accesses it through the internal service.

Useful checks:

```bash
kubectl get pods -n monitoring
kubectl get pods -n observability
kubectl get vmservicescrapes -A
kubectl get ingress -A
```

Application services must carry:

```yaml
app.kubernetes.io/part-of: casinoshiz
```

for `VMServiceScrape` selection.

---

## Tracing

Applications export OTLP to:

```text
otel-collector.observability.svc.cluster.local:4317
```

The collector forwards traces to Tempo.

Expected environment variables:

```text
OTEL_SERVICE_NAME
OTEL_EXPORTER_OTLP_ENDPOINT
```

Tempo uses a local PVC and seven-day retention.

Because Tempo is monolithic and stored on the same VPS, tracing data is
operational telemetry, not a durable business record.

---

## Network policy

Baseline ingress policies are included for:

- `casinoshiz`;
- `data`.

The policies allow:

- same-namespace application traffic;
- Traefik traffic to public application workloads;
- CasinoShiz workloads to data service ports;
- data namespace internal traffic.

These are baseline policies, not a complete zero-trust model.

Before deployment, verify the actual CNI used by k3s enforces NetworkPolicy.
A manifest existing in Git does not guarantee enforcement if the installed CNI
does not implement it.

---

## Common diagnostics

### Flux

```bash
flux get all -A
flux logs --all-namespaces --level=error
```

### Pods

```bash
kubectl get pods -A
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous
```

### HelmRelease

```bash
kubectl get helmreleases -A
kubectl describe helmrelease <name> -n <namespace>
```

### PVC

```bash
kubectl get pvc -A
kubectl describe pvc <name> -n <namespace>
```

### Ingress and certificates

```bash
kubectl get ingress -A
kubectl get certificates -A
kubectl get challenges -A
kubectl get orders -A
```

### Backup Jobs

```bash
kubectl get cronjobs,jobs -n data
kubectl logs -n data job/<job-name>
```

### Rendered configuration

```bash
go-task clean
go-task validate

less .task/rendered/casinoshiz.yaml
less .task/rendered/production.yaml
```

---

## Deployment checklist

### Repository

- [ ] `go-task validate` succeeds.
- [ ] `go-task placeholders` shows no unresolved production values.
- [ ] GitHub Actions validation succeeds.
- [ ] All images use immutable tags or digests.
- [ ] No plaintext secrets are committed.

### Host

- [ ] VPS IP and SSH access are confirmed.
- [ ] DNS records point to the VPS.
- [ ] Ports 22, 80 and 443 are open.
- [ ] Database and observability ports are not public.
- [ ] k3s node is `Ready`.

### GitOps

- [ ] Flux bootstrap succeeds.
- [ ] All Flux Kustomizations are ready.
- [ ] All HelmReleases are ready.
- [ ] cert-manager ClusterIssuer is ready.
- [ ] TLS certificates are issued.

### Data

- [ ] All StatefulSets are ready.
- [ ] All PVCs are bound.
- [ ] Application migrations succeed.
- [ ] Manual backup Jobs succeed.
- [ ] Off-site synchronization succeeds.
- [ ] Restore test succeeds.

### Application

- [ ] Frontend is reachable.
- [ ] Telegram webhook endpoint is reachable.
- [ ] Admin endpoint is protected.
- [ ] REST API health checks succeed.
- [ ] Identity and wallet gRPC connectivity succeeds.
- [ ] Game services are ready.
- [ ] HPA reports valid metrics.

### Observability

- [ ] Grafana is reachable.
- [ ] VictoriaMetrics receives application metrics.
- [ ] Tempo receives traces.
- [ ] Alertmanager is configured with a real notification destination.
- [ ] Backup failures generate alerts.

---

## What is deliberately not implemented

The following are not required for the initial single-node deployment:

- multi-node database replication;
- highly available Kubernetes control plane;
- distributed Tempo;
- distributed VictoriaMetrics cluster;
- database operators;
- service mesh;
- automatic failover;
- multi-region deployment.

These should be introduced only when reliability requirements justify their
operational complexity.

---

## Definition of ready

The infrastructure is ready for first production deployment when:

1. the latest repository state passes `go-task validate`;
2. all `CHANGE_ME` values are replaced;
3. SOPS-encrypted secrets exist;
4. DNS records resolve to the VPS;
5. application images exist in GHCR;
6. Flux reconciles successfully;
7. backups and at least one restore are tested.

Until all seven conditions are satisfied, the repository is a complete
deployment framework, but not a verified production installation.
