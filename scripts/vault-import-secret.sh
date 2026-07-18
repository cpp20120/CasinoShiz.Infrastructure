#!/usr/bin/env sh
set -eu

namespace=${1:-casinoshiz}
secret_name=${2:-casinoshiz-secrets}
vault_path=${3:-casinoshiz/app}

payload=$(kubectl get secret "$secret_name" -n "$namespace" -o json \
  | jq -c '{data: (.data | with_entries(.value |= @base64d))}')

printf '%s\n' "$payload" \
  | kubectl exec -i -n vault vault-0 -- env VAULT_TOKEN=root \
      vault write -format=json "secret/data/$vault_path" - >/dev/null

printf 'Imported %s/%s into secret/data/%s\n' "$namespace" "$secret_name" "$vault_path"
