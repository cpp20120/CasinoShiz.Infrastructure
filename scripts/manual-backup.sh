#!/usr/bin/env bash
set -euo pipefail

timestamp="$(date +%s)"
cronjobs=(
  postgres-backup
  redis-backup
  clickhouse-backup
  minio-backup
)

jobs=()

for cronjob in "${cronjobs[@]}"; do
  job="${cronjob}-manual-${timestamp}"
  kubectl create job \
    --from="cronjob/${cronjob}" \
    "$job" \
    -n data
  jobs+=("$job")
done

for job in "${jobs[@]}"; do
  kubectl wait \
    --for=condition=complete \
    "job/${job}" \
    -n data \
    --timeout=30m

  kubectl logs \
    "job/${job}" \
    -n data
done

echo "All manual backup Jobs completed."
