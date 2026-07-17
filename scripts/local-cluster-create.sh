#!/usr/bin/env bash
set -euo pipefail

cluster="${K3D_CLUSTER_NAME:-casinoshiz-local}"
registry="k3d-casinoshiz-registry.localhost"
registry_port="${K3D_REGISTRY_PORT:-5005}"

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not available." >&2
  exit 1
fi

if ! k3d registry list | grep -q "${registry}"; then
  k3d registry create casinoshiz-registry.localhost \
    --port "${registry_port}"
fi

if ! k3d cluster list | grep -q "^${cluster}[[:space:]]"; then
  k3d cluster create "${cluster}" \
    --servers 1 \
    --agents 0 \
    --registry-use "${registry}:${registry_port}" \
    --port "8080:80@loadbalancer" \
    --port "8443:443@loadbalancer" \
    --wait
fi

kubectl config use-context "k3d-${cluster}"
kubectl get nodes
