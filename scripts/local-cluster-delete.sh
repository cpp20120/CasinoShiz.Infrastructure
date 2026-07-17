#!/usr/bin/env bash
set -euo pipefail

cluster="${K3D_CLUSTER_NAME:-casinoshiz-local}"

k3d cluster delete "${cluster}" || true

if [[ "${DELETE_LOCAL_REGISTRY:-false}" == "true" ]]; then
  k3d registry delete casinoshiz-registry.localhost || true
fi
