#!/usr/bin/env bash
set -euo pipefail

wait_timeout="${WAIT_TIMEOUT:-300s}"

echo "Checking Flux..."
if command -v flux >/dev/null 2>&1; then
  flux get all -A
fi

echo "Waiting for data StatefulSets..."
for statefulset in postgres redis clickhouse minio; do
  kubectl rollout status "statefulset/${statefulset}" \
    -n data \
    --timeout="${wait_timeout}"
done

echo "Waiting for CasinoShiz Deployments..."
while IFS= read -r deployment; do
  kubectl rollout status "$deployment" \
    -n casinoshiz \
    --timeout="${wait_timeout}"
done < <(kubectl get deployments -n casinoshiz -o name)

echo "Checking PVCs..."
kubectl get pvc -A

unbound="$(
  kubectl get pvc -A \
    -o jsonpath='{range .items[?(@.status.phase!="Bound")]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}'
)"
if [[ -n "$unbound" ]]; then
  printf 'Unbound PVCs:\n%s\n' "$unbound" >&2
  exit 1
fi

echo "Checking certificates..."
kubectl get certificates -A

echo "Checking ingresses..."
kubectl get ingress -A

echo "Checking backup CronJobs..."
kubectl get cronjobs -n data

echo "Checking observability..."
kubectl get pods -n monitoring
kubectl get pods -n observability

echo "Checking application health from inside the cluster..."
for service in telegram-bff admin-bff rest-api; do
  kubectl run "health-${service}-$(date +%s)" \
    --rm \
    --restart=Never \
    --image=curlimages/curl:8.12.1 \
    -n casinoshiz \
    -- \
    -fsS "http://${service}.casinoshiz.svc.cluster.local:8080/health/ready"
done

echo "Post-deployment checks passed."
