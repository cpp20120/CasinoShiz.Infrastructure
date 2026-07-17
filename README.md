# CasinoShiz.Infrastructure

GitOps-инфраструктура для развёртывания CasinoShiz в Kubernetes.

Репозиторий содержит bootstrap хоста, k3s/k3d-кластеры, Flux, Helm chart приложения, stateful data services, observability, autoscaling, backup jobs, SOPS-ready secrets и эксплуатационные runbooks.

## Что здесь есть

### Kubernetes и GitOps

* k3s для production single-node VPS;
* k3d для полного локального окружения;
* Flux CD;
* staged reconciliation:

  * platform;
  * data;
  * application;
* Kustomize overlays для production и local;
* Helm chart CasinoShiz;
* локальный Docker registry для k3d;
* Taskfile для единых команд локально и в CI.

### Application workloads

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

Game services используют общий backend image с разным значением `Backend__Modules`.

### Data services

В namespace `data` разворачиваются:

* PostgreSQL;
* Redis;
* ClickHouse;
* MinIO.

PostgreSQL содержит отдельные базы:

* `backend`;
* `identity`;
* `wallet`.

Хранилища используют StatefulSet и `local-path` PVC.

### Backups

Для stateful services настроены Kubernetes CronJob:

| Время | Backup                   |
| ----- | ------------------------ |
| 02:15 | PostgreSQL logical dump  |
| 02:45 | Redis RDB и AOF          |
| 03:30 | ClickHouse native backup |
| 04:15 | MinIO mirror             |
| 05:30 | optional off-site sync   |

Все локальные backup сохраняются в отдельный PVC `data-backups`.

Retention:

* PostgreSQL — 14 дней;
* Redis — 14 дней;
* ClickHouse — 14 дней;
* MinIO — 7 дней.

Также предусмотрена optional синхронизация backup во внешний S3-compatible storage через `rclone`.

> Локальный backup на той же VPS защищает от случайного удаления, неудачной миграции и логической порчи, но не защищает от потери VPS или диска.

### Observability

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
metrics -> VictoriaMetrics
traces  -> OpenTelemetry Collector -> Tempo
```

Добавлены alert rules для:

* CrashLoopBackOff;
* недоступных Deployment;
* недоступных StatefulSet;
* частых рестартов контейнеров;
* незапущенных pods;
* заполнения PVC;
* PVC в `Pending` или `Lost`;
* `DiskPressure`;
* `MemoryPressure`;
* `NodeNotReady`;
* failed backup Jobs;
* suspended backup CronJobs;
* пропущенных backup schedules.

### Autoscaling

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

`ScaledObject` намеренно не добавлен, пока отсутствует реальный backlog metric, например:

* Redis Streams pending count;
* queue length;
* effect execution backlog;
* durable job count.

### Networking и TLS

Production environment использует:

* Traefik из k3s;
* cert-manager;
* Let's Encrypt;
* Kubernetes Ingress;
* baseline NetworkPolicy;
* Pod Security namespace labels.

Публично предполагается открывать только:

* frontend;
* Telegram BFF;
* Admin BFF;
* REST API;
* Grafana.

PostgreSQL, Redis, ClickHouse, MinIO, Tempo и OpenTelemetry Collector не должны быть доступны из интернета.

### Secrets

Secrets предназначены для хранения в Git через:

* SOPS;
* age;
* Flux SOPS decryption.

Приватный age key хранится вне Git.

В репозитории могут находиться только зашифрованные Secret manifests.

## Архитектура

```text
Internet
   |
   v
Traefik
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
   +--> /metrics --> VictoriaMetrics --> Grafana
   |
   +--> OTLP --> OpenTelemetry Collector --> Tempo
```

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
├── scripts/
│   ├── local-cluster-create.sh
│   ├── local-cluster-delete.sh
│   ├── local-flux-bootstrap.sh
│   ├── local-image-push.sh
│   ├── manual-backup.sh
│   ├── preflight.sh
│   ├── post-deploy-check.sh
│   └── cluster-status.sh
│
├── docs/
│   ├── LOCAL_FULL_SETUP.md
│   ├── OPERATIONS.md
│   ├── PRODUCTION_CHECKLIST.md
│   ├── RUNBOOKS.md
│   ├── DISASTER_RECOVERY.md
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

## Требования

Для локальной работы необходимы:

* Docker;
* kubectl;
* Helm;
* Kustomize;
* Task;
* Ansible;
* k3d;
* Flux CLI;
* SOPS;
* age;
* Git;
* jq;
* OpenSSL.

Для CachyOS или Arch Linux:

```bash
sudo pacman -S \
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

`k3d` и `flux` устанавливаются отдельно через официальные installers или подходящие Arch/AUR packages.

## Taskfile

Показать доступные команды:

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
go-task placeholders
go-task validate
go-task release:check
go-task preflight
go-task post-deploy
go-task backup:manual
go-task status
go-task clean
```

### Проверка manifests

```bash
go-task clean
go-task validate
```

Команда выполняет:

1. Helm lint;
2. Helm render;
3. Kustomize render;
4. basic plaintext-secret validation.

Rendered manifests сохраняются в:

```text
.task/rendered/casinoshiz.yaml
.task/rendered/production.yaml
```

## Полное локальное развёртывание

Полная пошаговая инструкция находится в:

```text
docs/LOCAL_FULL_SETUP.md
```

```sh
unzip -o CasinoShiz.Infrastructure.profile-installer.zip -d .
chmod +x scripts/install.py

python -m py_compile scripts/install.py
go-task clean
go-task validate
````

Общая последовательность:

### 1. Создать age key

```bash
mkdir -p ~/.config/sops/age
chmod 700 ~/.config/sops/age

age-keygen -o ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
```

Получить public recipient:

```bash
AGE_RECIPIENT="$(
  age-keygen -y ~/.config/sops/age/keys.txt
)"

echo "$AGE_RECIPIENT"
```

Подставить его в `.sops.yaml`.

### 2. Создать и зашифровать local secrets

```bash
cp \
  clusters/local/stages/data/data.secret.yaml.example \
  clusters/local/stages/data/data.secret.yaml

cp \
  clusters/local/stages/app/casinoshiz.secret.yaml.example \
  clusters/local/stages/app/casinoshiz.secret.yaml
```

После заполнения:

```bash
sops --encrypt --in-place \
  clusters/local/stages/data/data.secret.yaml

sops --encrypt --in-place \
  clusters/local/stages/app/casinoshiz.secret.yaml
```

Проверить:

```bash
grep -n 'ENC\[' clusters/local/stages/data/data.secret.yaml
grep -n 'ENC\[' clusters/local/stages/app/casinoshiz.secret.yaml
```

### 3. Создать k3d cluster и registry

```bash
./scripts/local-cluster-create.sh
```

Создаются:

```text
cluster:
casinoshiz-local

host registry:
localhost:5005

cluster registry:
k3d-casinoshiz-registry.localhost:5005
```

### 4. Собрать application images

В application repository:

```bash
docker compose build
docker image ls
```

Загрузить images в local registry:

```bash
./scripts/local-image-push.sh \
  <source-image:tag> \
  casinoshiz-backend
```

Необходимые repositories:

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

### 5. Установить Flux и передать age key

```bash
./scripts/local-flux-bootstrap.sh
```

Проверить:

```bash
flux get sources git -A
flux get kustomizations -A
flux get helmreleases -A

kubectl get pods -A
kubectl get pvc -A
```

### 6. Открыть локальные сервисы

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

## Production deployment

Production предполагает single-node VPS с k3s.

Порядок:

1. заполнить Ansible inventory;
2. заменить production `CHANGE_ME`;
3. настроить DNS;
4. создать production SOPS secrets;
5. указать immutable image tags или digests;
6. запустить Ansible bootstrap;
7. получить kubeconfig;
8. выполнить Flux bootstrap;
9. дождаться reconciliation;
10. проверить certificates;
11. проверить StatefulSet и PVC;
12. выполнить manual backups;
13. выполнить restore test;
14. проверить metrics и traces.

Ansible bootstrap:

```bash
cd ansible
ansible-playbook playbooks/site.yml
```

Flux bootstrap:

```bash
flux bootstrap github \
  --owner=cpp20120 \
  --repository=CasinoShiz.Infrastructure \
  --branch=main \
  --path=clusters/production \
  --personal
```

Перед production deployment:

```bash
go-task release:check
go-task preflight
```

После reconciliation:

```bash
go-task post-deploy
go-task backup:manual
go-task status
```

## Работа с SOPS

Открыть encrypted secret в editor:

```bash
sops clusters/local/stages/app/casinoshiz.secret.yaml
```

Расшифровать только в stdout:

```bash
sops --decrypt \
  clusters/local/stages/app/casinoshiz.secret.yaml
```

Изменения после редактирования:

```bash
git add clusters/local/stages/app/casinoshiz.secret.yaml
git commit -m "update application secrets"
git push
```

Затем:

```bash
flux reconcile source git casinoshiz-infrastructure \
  -n flux-system \
  --with-source
```

Приватный age key:

```text
~/.config/sops/age/keys.txt
```

Он не должен попадать в Git.

## Backup operations

Запустить все backup вручную:

```bash
go-task backup:manual
```

Или:

```bash
./scripts/manual-backup.sh
```

Проверить:

```bash
kubectl get cronjobs,jobs -n data
```

Logs:

```bash
kubectl logs \
  -n data \
  job/<job-name>
```

## Status и диагностика

Общий status:

```bash
go-task status
```

Flux:

```bash
flux get all -A
flux logs --all-namespaces --level=error
```

Pods:

```bash
kubectl get pods -A
kubectl get events -A --sort-by=.lastTimestamp
```

Проблемный pod:

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

## Удаление локального окружения

Удалить cluster, сохранив registry:

```bash
./scripts/local-cluster-delete.sh
```

Удалить cluster и registry:

```bash
DELETE_LOCAL_REGISTRY=true \
  ./scripts/local-cluster-delete.sh
```

Все local-path PVC и локальные backup внутри кластера будут удалены вместе с cluster.

## Документация

| Документ                       | Назначение                       |
| ------------------------------ | -------------------------------- |
| `docs/LOCAL_FULL_SETUP.md`     | Полное локальное развёртывание   |
| `docs/OPERATIONS.md`           | Архитектура и эксплуатация       |
| `docs/PRODUCTION_CHECKLIST.md` | Checklist перед production       |
| `docs/RUNBOOKS.md`             | Диагностика типовых проблем      |
| `docs/DISASTER_RECOVERY.md`    | Восстановление после аварии      |
| `docs/data-backups.md`         | Backup и restore                 |
| `SECURITY.md`                  | Security policy                  |
| `CONTRIBUTING.md`              | Правила изменения инфраструктуры |

## Ограничения

Текущая production architecture:

* один VPS;
* одна Kubernetes node;
* один local disk failure domain;
* stateful services без репликации;
* local-path storage;
* monolithic Tempo;
* single-node VictoriaMetrics.

Она подходит для текущего масштаба CasinoShiz, но не обеспечивает high availability.

При росте нагрузки можно отдельно перейти на:

* multi-node Kubernetes;
* external managed PostgreSQL;
* replicated ClickHouse;
* external S3;
* distributed VictoriaMetrics;
* distributed Tempo;
* отдельный backup host;
* KEDA scaling по реальной очереди.

## Готовность к production

Инфраструктура готова к первому production deployment, когда:

* `go-task validate` проходит;
* `go-task placeholders` не показывает production placeholders;
* GitHub Actions зелёный;
* SOPS secrets зашифрованы;
* age private key сохранён вне Git;
* application images опубликованы;
* DNS настроен;
* TLS certificates выпущены;
* Flux resources находятся в Ready;
* все PVC находятся в Bound;
* manual backups проходят;
* PostgreSQL и ClickHouse restore протестированы;
* Alertmanager доставляет test alert.



Images

Имена images нельзя надёжно вывести из инфраструктурного репозитория, поэтому для remote build используется явная карта:

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

Для каждого image installer делает:

docker compose build
docker tag
docker save
sudo k3s ctr images import

Helm values должны ссылаться на тот же target.
Installer нужно передать:
SSH user@IP
SSH key
ingress profile
repo URLs
domains
age key path
GitHub token для Flux bootstrap т.е. export GITHUB_TOKEN='github_pat_...'



т.е. полный набор шагов

# 1. Создал age key
age-keygen -o ~/.config/sops/age/keys.txt

# 2. Заполнил и зашифровал secrets
sops --encrypt --in-place data/data.secret.yaml
sops --encrypt --in-place \
  clusters/production/casinoshiz/casinoshiz.secret.yaml
sops --encrypt --in-place \
  clusters/production/casinoshiz/ghcr.secret.yaml

# 3. Указал images/domains/profile
$EDITOR charts/casinoshiz/values-production.yaml
$EDITOR deploy/installer.local.toml

# 4. Проверил
go-task clean
go-task validate

# 5. Отправил encrypted state в Git
git add .
git commit -m "configure production deployment"
git push

# 6. Запустил installer
export GITHUB_TOKEN='...'

python scripts/install.py \
  --config deploy/installer.local.toml

# 7. Проверил
export KUBECONFIG="$PWD/.deploy/kubeconfig"

flux get all -A
kubectl get pods -A
kubectl get pvc -A