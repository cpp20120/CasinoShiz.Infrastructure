# Disaster recovery

## Recovery objectives

This deployment runs on one VPS and one local disk failure domain.

Suggested initial objectives:

- business database RPO: 24 hours maximum;
- business database RTO: several hours;
- media/object RPO: 24 hours;
- telemetry data: best effort;
- infrastructure manifests: recoverable immediately from Git.

These are targets, not guarantees, until restore tests have been completed.

## Total VPS loss

1. Provision a new VPS.
2. Point the Ansible inventory to the new host.
3. Run the Ansible bootstrap.
4. Bootstrap Flux.
5. Install the encrypted secrets.
6. Wait for platform and data workloads.
7. Download off-site backups.
8. Restore PostgreSQL.
9. Restore ClickHouse.
10. Restore Redis only if its state is required.
11. Restore MinIO.
12. start CasinoShiz workloads.
13. Validate health, metrics and traces.
14. update DNS if the public IP changed.

## PostgreSQL corruption

1. stop writes or scale application workloads to zero;
2. preserve the current PVC before changing it;
3. choose the newest valid dump preceding corruption;
4. restore into a new database name;
5. run integrity checks and application queries;
6. update the application connection string;
7. resume workloads;
8. retain the corrupted database for forensic analysis.

## ClickHouse corruption

Event data should be restored into a separate database first.

```sql
RESTORE DATABASE cazinoshiz AS cazinoshiz_restored
FROM Disk('backup', '<timestamp>');
```

Validate row counts and representative event streams before replacing the
production database.

## Redis loss

Determine whether Redis contains:

- disposable cache data;
- durable queues;
- locks or leases;
- session state;
- rate-limit state.

Do not blindly restore stale distributed locks or leases. Restore only the data
classes whose semantics tolerate rollback.

## MinIO loss

Restore to a temporary bucket or temporary MinIO instance. Compare object counts
and sample checksums before promoting restored data.

## Restore test cadence

Run at least:

- monthly PostgreSQL restore test;
- monthly ClickHouse restore test;
- quarterly full VPS rebuild test;
- restore test after any backup format or version change.

Record:

- backup timestamp;
- restore duration;
- validation performed;
- missing or corrupt data;
- corrective actions.
