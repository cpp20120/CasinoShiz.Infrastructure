#!/usr/bin/env bash
set -euo pipefail

age_key_file="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"

if [[ ! -f "${age_key_file}" ]]; then
  echo "Age key not found: ${age_key_file}" >&2
  exit 1
fi

flux install

kubectl create namespace flux-system \
  --dry-run=client \
  -o yaml \
  | kubectl apply -f -

kubectl create secret generic sops-age \
  --namespace=flux-system \
  --from-file=age.agekey="${age_key_file}" \
  --dry-run=client \
  -o yaml \
  | kubectl apply -f -

kubectl apply -k clusters/local/bootstrap

flux reconcile source git casinoshiz-infrastructure \
  --namespace flux-system \
  --with-source

flux get kustomizations -A
