# Single-node data and backups

This layout runs PostgreSQL, Redis, ClickHouse and MinIO on one k3s node using
`local-path` PVCs.

## Backup schedule

- PostgreSQL logical dumps: 02:15 Europe/Helsinki, retained locally for 14 days.
- Redis RDB/AOF copy: 02:45, retained locally for 14 days.
- ClickHouse native BACKUP: 03:30, retained locally for 14 days.
- MinIO mirror: 04:15, retained locally for 7 days.
- Optional external sync: 05:30, initially suspended.

All local backups are written to the `data-backups` PVC.

## Important limitation

A backup PVC on the same VPS protects against:

- accidental deletion;
- bad migrations;
- logical corruption discovered before retention expires;
- restoring an individual database.

It does not protect against:

- VPS loss;
- disk failure;
- filesystem corruption affecting the whole node;
- account suspension or provider failure.

Enable the `backup-offsite-sync` CronJob after configuring `rclone-config`.
A backup is not considered reliable until a restore has been tested.

## Secret installation

Copy the examples, replace values, encrypt with SOPS, then add the encrypted
files to the appropriate Application:

```bash
cp data/data.secret.yaml.example data/data.secret.yaml
sops --encrypt --in-place data/data.secret.yaml
```

Do not commit plaintext secrets.

## Restore examples

PostgreSQL:

```bash
createdb -h postgres.data.svc.cluster.local -U postgres restored_backend
pg_restore -h postgres.data.svc.cluster.local -U postgres   --dbname restored_backend /backup/postgres/<timestamp>/backend.dump
```

ClickHouse:

```sql
RESTORE DATABASE cazinoshiz
FROM Disk('backup', '<timestamp>');
```

Redis and MinIO should be restored into an isolated test workload first,
validated, and only then promoted.
