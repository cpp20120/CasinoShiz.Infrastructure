#!/usr/bin/env bash
set -euo pipefail

if (($# != 2)); then
  echo "Usage: $0 <source-image:tag> <target-repository>" >&2
  echo "Example: $0 casinoshiz-backend:latest casinoshiz-backend" >&2
  exit 2
fi

source_image="$1"
target_repository="$2"
host_registry="${LOCAL_REGISTRY_HOST:-localhost:5005}"
target="${host_registry}/${target_repository}:local"

docker image inspect "${source_image}" >/dev/null
docker tag "${source_image}" "${target}"
docker push "${target}"

echo "Pushed ${target}"
