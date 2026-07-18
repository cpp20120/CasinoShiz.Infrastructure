# CasinoShiz.Infrastructure

GitOps-инфраструктура для локального и production-развёртывания CasinoShiz в Kubernetes.

Репозиторий содержит:

* bootstrap single-node VPS;
* локальный k3d-кластер;
* k3s production cluster;
* Argo CD;
* Helm chart приложения;
* stateful data services;
* observability;
* autoscaling;
* NetworkPolicy;
* backup и restore workflows;
* SOPS-encrypted Kubernetes Secrets;
* единый operational CLI;
* эксплуатационные runbooks и проверки готовности.

Текущая архитектура рассчитана на один VPS и текущий масштаб CasinoShiz. Она не является high-availability кластером, но покрывает полный lifecycle приложения: от установки k3s до backup, restore и диагностики.

---

## Архитектурные границы

Инструменты разделены по ответственности:

```text
Taskfile
  └── удобный публичный интерфейс команд

Python CLI
  └── orchestration локальных инструментов и Kubernetes operations

Ansible
  └── bootstrap и настройка VPS/k3s

Argo CD
  └── постоянная GitOps reconciliation внутри Kubernetes

Helm
  └── шаблонизация application workloads

Kustomize
  └── композиция platform, data и application manifests

SOPS + age
  └── encrypted Kubernetes Secrets в Git
```

Основная production-цепочка:

```text
GitHub Actions
  ├── build/test application
  └── push images в GHCR

Git repository
  └── desired Kubernetes state

Ansible
  └── устанавливает и настраивает k3s на VPS

Argo CD
  └── читает Git и применяет manifests

k3s/containerd
  └── получает application images из GHCR
```

---

## Что уже реализовано

### Kubernetes и GitOps

* k3s для production single-node VPS;
* k3d для локального Kubernetes-окружения;
* Argo CD;
* staged reconciliation:

  * platform;
  * data;
  * application;
* Helm chart CasinoShiz;
* Kustomize composition для production и local;
* локальный Docker registry для k3d;
* Taskfile для единых локальных и CI-команд;
* SOPS decryption через Argo CD;
* production preflight и post-deploy checks;
* cluster status и diagnostics commands.

### Host bootstrap

Ansible отвечает за:

* подключение к VPS по SSH;
* установку системных пакетов;
* настройку каталогов;
* базовую настройку host firewall и sysctl;
* установку k3s;
* выбор ingress-профиля;
* конфигурацию systemd/k3s;
* подготовку хоста к Argo CD bootstrap.

Ansible запускается локально и конфигурирует удалённый VPS.

На VPS Ansible заранее устанавливать не требуется.

```text
локальная машина
  └── ansible-playbook
        └── SSH
              └── VPS
```

### Operational CLI

Repository-level shell scripts сведены в единый CLI:

```bash
python scripts/infra.py --help
```

Группы команд:

```text
local     локальный k3d cluster, registry и Argo CD bootstrap
sops      age/SOPS и генерация Secret manifests
cluster   preflight, status и post-deploy проверки
backup    ручной запуск backup Jobs
restore   restore и restore verification
```

Taskfile остаётся публичным facade и вызывает Python CLI внутри.

---

## Application workloads

Helm chart умеет разворачивать:

* frontend;
* identity service;
* wallet service;
* Telegram BFF;
* Discord BFF;
* Admin BFF;
* REST API;
* game services:

  * dice;
  * dicecube;
  * darts;
  * football;
  * basketball;
  * bowling;
  * transfer;
  * redeem;
  * leaderboard;
  * pixelbattle;
  * pick;
  * blackjack;
  * horse;
  * challenges;
  * poker;
  * secrethitler;
  * meta;
  * admin.

Game services используют общий backend image с различными значениями:

```text
Backend__Modules
```

---

## Data services

В namespace `data` разворачиваются:

* PostgreSQL;
* Redis;
* ClickHouse;
* MinIO.

PostgreSQL содержит отдельные базы:

* `backend`;
* `identity`;
* `wallet`.

Stateful services используют StatefulSet и persistent storage:

```text
postgres-0
redis-0
clickhouse-0
minio-0
```

Storage основан на `local-path` PVC.

Это обеспечивает сохранение данных при перезапуске Pod, но не обеспечивает отказоустойчивость при потере VPS или диска.

---

## Backups

Для stateful services настроены Kubernetes CronJob:

| Время | Backup                   |
| ----- | ------------------------ |
| 02:15 | PostgreSQL logical dump  |
| 02:45 | Redis RDB и AOF          |
| 03:30 | ClickHouse native backup |
| 04:15 | MinIO mirror             |
| 05:30 | optional off-site sync   |

Все локальные backup сохраняются в отдельный PVC:

```text
data-backups
```

Retention:

* PostgreSQL — 14 дней;
* Redis — 14 дней;
* ClickHouse — 14 дней;
* MinIO — 7 дней.

Также предусмотрена optional синхронизация во внешний S3-compatible storage через `rclone`.

> Backup на той же VPS защищает от случайного удаления, неудачной миграции и логической порчи, но не защищает от полной потери VPS или её диска.

### Ручной запуск backup

```bash
go-task backup:manual
```

Эквивалентная прямая команда:

```bash
python scripts/infra.py backup run
```

Проверка:

```bash
kubectl get cronjobs,jobs -n data
```

Logs конкретного Job:

```bash
kubectl logs -n data job/<job-name>
```

---

## Restore

Для backup workflows добавлены исполняемые restore operations.

Restore по умолчанию безопасен:

* PostgreSQL восстанавливается в новую database;
* ClickHouse восстанавливается в новую database;
* Redis проверяется в изолированном временном экземпляре;
* MinIO восстанавливается в новый bucket.

Production data не перезаписывается без явного destructive режима или явно заданного target.

### PostgreSQL

Восстановить latest backup базы `backend`:

```bash
python scripts/infra.py restore postgres \
  --database backend
```

Выбрать backup и target:

```bash
python scripts/infra.py restore postgres \
  --backup 20260717T021500Z \
  --database backend \
  --target backend_restore_test
```

Restore выполняет:

1. проверку backup-файла;
2. проверку `SHA256SUMS`;
3. создание новой базы;
4. `pg_restore --exit-on-error`;
5. проверку наличия пользовательских таблиц.

### ClickHouse

```bash
python scripts/infra.py restore clickhouse \
  --source-db cazinoshiz
```

Явный backup и target:

```bash
python scripts/infra.py restore clickhouse \
  --backup 20260717T033000Z \
  --source-db cazinoshiz \
  --target-db cazinoshiz_restore_test
```

### Redis

Безопасная проверка backup:

```bash
python scripts/infra.py restore redis \
  --mode verify
```

Проверка выполняет:

1. копирование `dump.rdb` в isolated Job;
2. запуск `redis-check-rdb`;
3. запуск временного Redis только внутри Job;
4. проверку `PING`;
5. проверку `DBSIZE`.

Destructive replacement production Redis:

```bash
python scripts/infra.py restore redis \
  --mode replace \
  --backup 20260717T024500Z \
  --confirm REPLACE_REDIS
```

При replacement Redis StatefulSet сначала масштабируется в `0`, после чего содержимое PVC заменяется.

### MinIO

Restore требует имя исходного bucket:

```bash
python scripts/infra.py restore minio \
  --bucket casino-assets
```

По умолчанию будет создан отдельный bucket:

```text
casino-assets-restore-<timestamp>
```

Явный target:

```bash
python scripts/infra.py restore minio \
  --bucket casino-assets \
  --target-bucket casino-assets-restore-test
```

### Restore smoke test

```bash
go-task restore:smoke
```

Или:

```bash
python scripts/infra.py restore smoke
```

С явными значениями:

```bash
POSTGRES_DATABASE=backend \
CLICKHOUSE_DATABASE=cazinoshiz \
MINIO_BUCKET=casino-assets \
python scripts/infra.py restore smoke
```

PostgreSQL и ClickHouse restore-базы намеренно сохраняются после smoke test для ручной проверки.

---

## Observability

В репозитории настроены:

* VictoriaMetrics;
* VMAgent;
* VMAlert;
* Alertmanager;
* Grafana;
* OpenTelemetry Collector;
* Tempo.

Applications экспортируют:

```text
metrics -> VictoriaMetrics -> Grafana
traces  -> OpenTelemetry Collector -> Tempo
```

Добавлены alert rules для:

* CrashLoopBackOff;
* недоступных Deployment;
* недоступных StatefulSet;
* частых рестартов контейнеров;
* незапущенных Pods;
* заполнения PVC;
* PVC в `Pending` или `Lost`;
* `DiskPressure`;
* `MemoryPressure`;
* `NodeNotReady`;
* failed backup Jobs;
* suspended backup CronJobs;
* пропущенных backup schedules.

---

## Autoscaling

Настроен CPU-based HPA для:

* Telegram BFF;
* Discord BFF;
* REST API;
* game services.

Default policy:

```text
min replicas: 1
max replicas: 4
target CPU: 65%
scale-down stabilization: 300 seconds
```

Также установлен KEDA operator.

`ScaledObject` намеренно не добавлен, пока отсутствует реальная backlog metric:

* Redis Streams pending count;
* queue length;
* effect execution backlog;
* durable job count.

---

## Networking и TLS

Production может использовать один из двух ingress-профилей:

* Traefik, встроенный в k3s;
* минимальный nginx profile с отключением встроенного Traefik.

Также используются:

* cert-manager;
* Let's Encrypt;
* Kubernetes Ingress;
* baseline NetworkPolicy;
* Pod Security namespace labels.

Для NetworkPolicy на текущем этапе используется стандартный k3s networking stack:

```text
Flannel
+
встроенный kube-router NetworkPolicy controller
```

Cilium или Calico для текущего single-node масштаба не требуются.

Публично предполагается открывать только:

* frontend;
* Telegram BFF;
* Admin BFF;
* REST API;
* Grafana.

Не должны быть доступны из интернета:

* PostgreSQL;
* Redis;
* ClickHouse;
* MinIO;
* Tempo;
* OpenTelemetry Collector;
* internal application services.

---

## Secrets

Secrets хранятся в Git только в зашифрованном виде:

* SOPS;
* age;
* Argo CD SOPS decryption.

Приватный age key хранится вне Git:

```text
~/.config/sops/age/keys.txt
```

В Git могут находиться только encrypted Secret manifests.

### Инициализация SOPS

```bash
python scripts/infra.py sops init
```

Команда:

1. создаёт age identity, если её ещё нет;
2. получает public age recipient;
3. создаёт `.sops.yaml`;
4. оставляет private key только на локальной машине.

### Создание application Secret

```bash
python scripts/infra.py sops app-secret \
  ../CasinoShiz/.env.production
```

Plaintext env используется только как input.

Результат сразу шифруется и сохраняется как Kubernetes Secret manifest.

### Создание GHCR pull Secret

```bash
export GHCR_USERNAME=cpp20120

read -rsp 'GHCR token: ' GHCR_TOKEN
export GHCR_TOKEN

python scripts/infra.py sops ghcr-secret

unset GHCR_TOKEN
```

### Шифрование существующего Secret

```bash
python scripts/infra.py sops encrypt \
  data/data.secret.yaml
```

Можно передать несколько файлов:

```bash
python scripts/infra.py sops encrypt \
  data/data.secret.yaml \
  clusters/production/casinoshiz/casinoshiz.secret.yaml \
  clusters/production/casinoshiz/ghcr.secret.yaml
```

### Проверка SOPS

```bash
go-task sops:check
```

Или:

```bash
python scripts/infra.py sops check
```

Проверяется, что tracked production `*.secret.yaml`:

* имеет `kind: Secret`;
* содержит SOPS metadata;
* содержит `ENC[AES256_GCM,...]`;
* расшифровывается текущим age identity;
* имеет корректный MAC.

Plaintext при проверке не выводится.

### Argo CD decryption

В Argo CD Application используется:

```yaml
spec:
  decryption:
    provider: sops
    secretRef:
      name: sops-age
```

В namespace `argocd` должен существовать Secret:

```text
sops-age
```

с private age identity.

---

## Архитектура сервисов

```text
Internet
   |
   v
Traefik или nginx
   |
   +--> frontend
   +--> telegram-bff
   +--> admin-bff
   +--> rest-api
            |
            +--> identity
            +--> wallet
            +--> game-*
            |
            +--> PostgreSQL
            +--> Redis
            +--> ClickHouse
            +--> MinIO

Applications
   |
   +--> /metrics
   |      |
   |      v
   |   VictoriaMetrics
   |      |
   |      v
   |    Grafana
   |
   +--> OTLP
          |
          v
   OpenTelemetry Collector
          |
          v
        Tempo
```

---

## Структура репозитория

```text
.
├── ansible/
│   ├── inventory/
│   ├── playbooks/
│   └── roles/
│
├── charts/
│   └── casinoshiz/
│       ├── templates/
│       ├── values.yaml
│       └── values-production.yaml
│
├── clusters/
│   ├── local/
│   │   ├── bootstrap/
│   │   └── stages/
│   │       ├── platform/
│   │       ├── data/
│   │       └── app/
│   │
│   └── production/
│
├── data/
│   ├── backup-storage/
│   ├── postgres/
│   ├── redis/
│   ├── clickhouse/
│   └── minio/
│
├── platform/
│   ├── namespaces/
│   ├── cert-manager/
│   ├── keda/
│   ├── monitoring/
│   ├── tracing/
│   └── network-policies/
│
├── deploy/
│   ├── installer.example.toml
│   └── installer.local.toml
│
├── profiles/
│   ├── traefik/
│   └── nginx/
│
├── scripts/
│   ├── infra.py
│   └── install.py
│
├── docs/
│   ├── LOCAL_FULL_SETUP.md
│   ├── OPERATIONS.md
│   ├── OPERATIONS_CLI.md
│   ├── PRODUCTION_CHECKLIST.md
│   ├── RUNBOOKS.md
│   ├── DISASTER_RECOVERY.md
│   ├── RESTORE.md
│   ├── SOPS.md
│   └── data-backups.md
│
├── .github/
│   ├── workflows/
│   ├── CODEOWNERS
│   └── dependabot.yml
│
├── Taskfile.yml
├── .sops.yaml
├── .yamllint.yml
├── renovate.json5
├── SECURITY.md
└── CONTRIBUTING.md
```

---

## Требования

Для локальной работы необходимы:

* Python 3;
* Docker;
* kubectl;
* Helm;
* Kustomize;
* Task;
* Ansible;
* k3d;
* Argo CD CLI;
* SOPS;
* age;
* Git;
* jq;
* OpenSSL.

Для CachyOS или Arch Linux:

```bash
sudo pacman -S \
  python \
  docker \
  docker-compose \
  kubectl \
  helm \
  kustomize \
  go-task \
  ansible \
  age \
  sops \
  jq \
  openssl \
  git
```

`k3d` и `helm` устанавливаются отдельно через официальные installers или подходящие Arch/AUR packages.

---

## Taskfile

Показать команды:

```bash
go-task --list
```

Основные команды:

```bash
go-task tools
go-task lint
go-task yaml:lint
go-task render:chart
go-task render:cluster
go-task ansible:check
go-task secrets:check
go-task sops:init
go-task sops:check
go-task validate
go-task release:check
go-task preflight
go-task post-deploy
go-task backup:manual
go-task restore:postgres
go-task restore:clickhouse
go-task restore:redis:verify
go-task restore:minio
go-task restore:smoke
go-task status
go-task clean
```

Taskfile является удобным facade.

Сложная orchestration-логика находится в:

```text
scripts/infra.py
```

---

## Validation

Основная проверка:

```bash
go-task clean
go-task validate
```

Validation включает:

1. Helm lint;
2. Helm render;
3. Kustomize render;
4. проверку plaintext secrets;
5. SOPS validation;
6. проверку итоговых rendered manifests.

Rendered manifests сохраняются в:

```text
.task/rendered/casinoshiz.yaml
.task/rendered/production.yaml
```

### Helm templates и yamllint

Файлы:

```text
charts/*/templates/*.yaml
```

не являются обычным YAML до выполнения Helm render.

Они содержат Go template expressions:

```text
{{ .Values.* }}
{{- if ... }}
{{ include ... }}
```

Поэтому сырые Helm templates нельзя проверять обычным `yamllint`.

Правильная последовательность:

```text
helm lint
→ helm template
→ yamllint rendered YAML
→ kubeconform rendered YAML
```

Сырые `charts/**/templates/**` должны быть исключены из прямого `yamllint`.

Пример:

```bash
helm template casinoshiz charts/casinoshiz \
  --namespace casinoshiz \
  -f charts/casinoshiz/values-production.yaml \
  > .task/rendered/casinoshiz.yaml

yamllint .task/rendered/casinoshiz.yaml
```

---

## Локальное окружение

Создать local k3d cluster:

```bash
python scripts/infra.py local create
```

Создаются:

```text
cluster:
casinoshiz-local

host registry:
localhost:5005

cluster registry:
k3d-casinoshiz-registry.localhost:5000
```

### Local images

В application repository:

```bash
docker compose build
docker image ls
```

Загрузить image в local registry:

```bash
python scripts/infra.py local image-push \
  <source-image:tag> \
  casinoshiz-backend
```

Основные repositories:

```text
casinoshiz-backend
casinoshiz-identity
casinoshiz-wallet
casinoshiz-telegram-bff
casinoshiz-admin-bff
casinoshiz-rest-api
casinoshiz-frontend
```

Проверить registry:

```bash
curl -fsS http://localhost:5005/v2/_catalog | jq
```

### Local Argo CD bootstrap

```bash
python scripts/infra.py local argocd-bootstrap
```

Проверить:

```bash
kubectl get applications -n argocd
kubectl get applications -n argocd
kubectl get applications -n argocd

kubectl get pods -A
kubectl get pvc -A
```

### Port forwarding

Frontend:

```bash
kubectl port-forward \
  -n casinoshiz \
  service/frontend \
  3000:80
```

REST API:

```bash
kubectl port-forward \
  -n casinoshiz \
  service/rest-api \
  8088:8080
```

Grafana:

```bash
kubectl get services -n monitoring

kubectl port-forward \
  -n monitoring \
  service/vmks-grafana \
  3001:80
```

MinIO:

```bash
kubectl port-forward \
  -n data \
  service/minio \
  9000:9000 \
  9001:9001
```

### Удаление local cluster

Удалить cluster, сохранив registry:

```bash
python scripts/infra.py local delete
```

Удалить cluster и registry:

```bash
DELETE_LOCAL_REGISTRY=true \
python scripts/infra.py local delete
```

Local PVC и backup data внутри k3d cluster будут удалены вместе с cluster.

---

## Production deployment

Production рассчитан на single-node VPS с k3s.

Installer получает:

* SSH target `user@IP`;
* SSH key;
* ingress profile;
* repository URLs;
* domains;
* age key path;
* GitHub token для Argo CD bootstrap;
* image mapping для optional remote/local build mode.

Пример запуска:

```bash
export GITHUB_TOKEN='github_pat_...'

python scripts/install.py \
  --config deploy/installer.local.toml
```

Installer:

1. читает TOML configuration;
2. проверяет SSH;
3. выбирает ingress profile;
4. генерирует Ansible inventory и variables;
5. запускает Ansible;
6. устанавливает k3s;
7. получает kubeconfig;
8. создаёт `argocd/sops-age`;
9. bootstrap-ит Argo CD;
10. ждёт reconciliation;
11. выполняет readiness checks.

### Production flow

```text
1. Создать age key
2. Создать и зашифровать Secrets
3. Указать images и domains
4. Запустить validate
5. Commit encrypted desired state
6. Push в Git
7. Запустить installer
8. Проверить Argo CD
9. Проверить Pods и PVC
10. Запустить backup
11. Запустить restore smoke test
12. Проверить reboot/failure recovery
```

### Полный набор команд

#### 1. Инициализация age/SOPS

```bash
python scripts/infra.py sops init
```

#### 2. Application Secret

```bash
python scripts/infra.py sops app-secret \
  ../CasinoShiz/.env.production
```

#### 3. GHCR Secret

```bash
export GHCR_USERNAME=cpp20120
export GHCR_TOKEN='...'

python scripts/infra.py sops ghcr-secret

unset GHCR_TOKEN
```

#### 4. Production values

```bash
$EDITOR charts/casinoshiz/values-production.yaml
$EDITOR deploy/installer.local.toml
```

#### 5. Проверка

```bash
go-task clean
go-task validate
go-task release:check
```

#### 6. Git commit

```bash
git add .
git commit -m "configure production deployment"
git push
```

#### 7. Installer

```bash
export GITHUB_TOKEN='...'

python scripts/install.py \
  --config deploy/installer.local.toml
```

#### 8. Kubeconfig

```bash
export KUBECONFIG="$PWD/.deploy/kubeconfig"
```

#### 9. Проверка кластера

```bash
kubectl get applications -n argocd
kubectl get pods -A
kubectl get pvc -A
kubectl get events -A --sort-by=.lastTimestamp
```

#### 10. Backup и restore

```bash
go-task backup:manual
go-task restore:smoke
```

---

## Optional application image build

Имена images нельзя надёжно вывести автоматически из инфраструктурного репозитория, поэтому optional build/import mode использует явную карту:

```toml
[deployment]
build_application_images = true

[images]
backend = {
  source = "compose-backend:latest",
  target = "casinoshiz-backend:local"
}

identity = {
  source = "compose-identity:latest",
  target = "casinoshiz-identity:local"
}
```

Для каждого image installer выполняет:

```text
docker compose build
docker tag
docker save
sudo k3s ctr images import
```

Helm values должны ссылаться на тот же target.

Для обычного production режима предпочтительнее GHCR:

```text
GitHub Actions
→ GHCR
→ k3s/containerd pull
```

Application repository на VPS при этом не требуется.

---

## Status и диагностика

Общий status:

```bash
go-task status
```

Или:

```bash
python scripts/infra.py cluster status
```

Argo CD:

```bash
kubectl get applications -n argocd
kubectl logs -n argocd deployment/argocd-application-controller
```

Pods:

```bash
kubectl get pods -A
kubectl get events -A --sort-by=.lastTimestamp
```

Проблемный Pod:

```bash
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous
```

PVC:

```bash
kubectl get pvc -A
kubectl describe pvc <name> -n <namespace>
```

Certificates:

```bash
kubectl get certificates -A
kubectl get challenges -A
kubectl get orders -A
```

Resources:

```bash
kubectl top nodes
kubectl top pods -A --sort-by=memory
```

---

## Failure tests

Failure tests проверяют восстановление после отказов и сохранность данных.

Удаление Pod:

```bash
kubectl delete pod -n data postgres-0
kubectl delete pod -n data redis-0
kubectl delete pod -n data clickhouse-0
kubectl delete pod -n data minio-0
```

После пересоздания необходимо проверить сохранность данных.

Проверка reboot:

```bash
sudo reboot
```

После загрузки:

```bash
kubectl get pods -A
kubectl get applications -n argocd
```

Проверка NetworkPolicy:

```text
frontend → PostgreSQL        denied
backend → PostgreSQL         allowed
backend → Redis              allowed
random Pod → ClickHouse      denied
workloads → kube-dns         allowed
ingress → public services    allowed
```

---

## Документация

| Документ                       | Назначение                       |
| ------------------------------ | -------------------------------- |
| `docs/LOCAL_FULL_SETUP.md`     | Полное локальное развёртывание   |
| `docs/OPERATIONS.md`           | Архитектура и эксплуатация       |
| `docs/OPERATIONS_CLI.md`       | Единый Python CLI                |
| `docs/PRODUCTION_CHECKLIST.md` | Checklist перед production       |
| `docs/RUNBOOKS.md`             | Диагностика типовых проблем      |
| `docs/DISASTER_RECOVERY.md`    | Восстановление после аварии      |
| `docs/RESTORE.md`              | Restore operations               |
| `docs/SOPS.md`                 | SOPS и age                       |
| `docs/data-backups.md`         | Backup storage и retention       |
| `SECURITY.md`                  | Security policy                  |
| `CONTRIBUTING.md`              | Правила изменения инфраструктуры |

---

## Ограничения

Текущая production architecture:

* один VPS;
* одна Kubernetes node;
* один local disk failure domain;
* stateful services без репликации;
* local-path storage;
* standalone MinIO;
* single-node ClickHouse;
* monolithic Tempo;
* single-node VictoriaMetrics.

Она подходит для текущего масштаба CasinoShiz, но не обеспечивает high availability.

При росте нагрузки можно отдельно перейти на:

* multi-node Kubernetes;
* внешний или managed PostgreSQL;
* replicated ClickHouse;
* внешний S3;
* distributed VictoriaMetrics;
* distributed Tempo;
* отдельный backup host;
* OpenTofu для создания VPS, firewall и DNS;
* KEDA scaling по реальной очереди;
* отдельные failure domains.

OpenTofu не требуется для управления текущим Kubernetes desired state.

Внутри кластера основным владельцем ресурсов остаётся Argo CD.

---
