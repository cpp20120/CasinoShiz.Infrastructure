# Backup restore runbook

Backups are useful only when restore procedures are executable and tested.

All restore scripts use the current `KUBECONFIG` and the `data` namespace by
default.

## Safety model

Safe defaults:

- PostgreSQL restores into a new database.
- ClickHouse restores into a new database.
- Redis starts an isolated temporary instance and validates the RDB.
- MinIO restores into a new bucket.

Production replacement requires explicit target names or destructive flags.

## Prerequisites

```bash
kubectl get pvc -n data
kubectl get cronjob -n data
kubectl get pods -n data
```

Expected storage:

```text
data-backups
data-postgres-0
data-redis-0
data-clickhouse-0
data-minio-0
```

## PostgreSQL

Restore the latest `backend.dump` into a timestamped database:

```bash
./scripts/restore-postgres.sh --database backend
```

Select a backup:

```bash
./scripts/restore-postgres.sh   --backup 20260717T021500Z   --database backend
```

Choose a target:

```bash
./scripts/restore-postgres.sh   --database backend   --target backend_restore_test
```

The script validates `SHA256SUMS`, creates the target database, runs
`pg_restore --exit-on-error`, and checks that user tables exist.

## ClickHouse

```bash
./scripts/restore-clickhouse.sh   --source-db cazinoshiz
```

Explicit backup and target:

```bash
./scripts/restore-clickhouse.sh   --backup 20260717T033000Z   --source-db cazinoshiz   --target-db cazinoshiz_restore_test
```

The source database is restored under a new database name.

## Redis

Safe verification:

```bash
./scripts/restore-redis.sh --mode verify
```

This:

1. copies `dump.rdb` into an isolated Job;
2. runs `redis-check-rdb`;
3. starts a loopback-only temporary Redis;
4. checks `PING` and `DBSIZE`;
5. deletes the Job.

Production replacement is destructive:

```bash
./scripts/restore-redis.sh   --mode replace   --backup 20260717T024500Z   --confirm REPLACE_REDIS
```

The script scales the Redis StatefulSet to zero before rewriting its PVC. If
the copy fails, Redis remains scaled down so the failed data is not started
silently.

## MinIO

A bucket name is required because the backup directory contains multiple
buckets.

```bash
./scripts/restore-minio.sh   --bucket casino-assets
```

This creates a timestamped target bucket.

Explicit destination:

```bash
./scripts/restore-minio.sh   --bucket casino-assets   --target-bucket casino-assets-restore-test
```

Existing destinations are rejected unless `--overwrite` is supplied.

## Restore smoke test

```bash
POSTGRES_DATABASE=backend CLICKHOUSE_DATABASE=cazinoshiz MINIO_BUCKET=casino-assets ./scripts/restore-smoke-test.sh
```

Or:

```bash
go-task restore:smoke
```

The smoke test intentionally retains restored PostgreSQL and ClickHouse
databases for manual inspection. The final output prints cleanup commands.

## Environment overrides

```bash
export NAMESPACE=data
export BACKUP_PVC=data-backups
```

## Recommended schedule

Run a restore smoke test:

- after changing backup manifests;
- after database version upgrades;
- at least monthly;
- before deleting old backup generations;
- after moving backup storage or off-site replication.
