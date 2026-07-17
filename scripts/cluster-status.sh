#!/usr/bin/env bash
set -euo pipefail

echo "== Nodes =="
kubectl get nodes -o wide

echo
echo "== Flux =="
if command -v flux >/dev/null 2>&1; then
  flux get all -A
else
  echo "flux CLI is not installed"
fi

echo
echo "== Workloads =="
kubectl get deployments,statefulsets -A

echo
echo "== Pods not Running or Completed =="
kubectl get pods -A \
  --field-selector=status.phase!=Running,status.phase!=Succeeded \
  || true

echo
echo "== PVCs =="
kubectl get pvc -A

echo
echo "== Ingresses =="
kubectl get ingress -A

echo
echo "== Certificates =="
kubectl get certificates -A 2>/dev/null || true

echo
echo "== Data Jobs =="
kubectl get cronjobs,jobs -n data

echo
echo "== Recent warning events =="
kubectl get events -A \
  --field-selector=type=Warning \
  --sort-by=.lastTimestamp \
  | tail -n 50
