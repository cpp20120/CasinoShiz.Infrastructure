#!/usr/bin/env sh
set -eu

# Local bootstrap only. Production must seed the same fields through the
# production Vault workflow and must not use the dev root token.
vault_namespace=${VAULT_NAMESPACE:-vault}
vault_pod=${VAULT_POD:-vault-0}
vault_token=${VAULT_TOKEN:-root}
vault_path=${VAULT_PATH:-secret/casinoshiz/sso}

random_secret() {
  openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | cut -c1-40
}

vault_get() {
  field=$1
  kubectl exec -n "$vault_namespace" "$vault_pod" -- \
    env VAULT_TOKEN="$vault_token" \
    vault kv get -field="$field" "$vault_path" 2>/dev/null || true
}

admin_password=$(vault_get admin-password)
postgres_admin_password=$(vault_get postgres-admin-password)
postgres_password=$(vault_get postgres-password)
grafana_client_secret=$(vault_get grafana-client-secret)
argocd_client_secret=$(vault_get argocd-client-secret)
sso_admin_password=$(vault_get sso-admin-password)

: "${admin_password:=$(random_secret)}"
: "${postgres_admin_password:=$(random_secret)}"
: "${postgres_password:=$(random_secret)}"
: "${grafana_client_secret:=$(random_secret)}"
: "${argocd_client_secret:=$(random_secret)}"
: "${sso_admin_password:=$(random_secret)}"

sso_admin_user=${SSO_ADMIN_USER:-admin}

kubectl exec -n "$vault_namespace" "$vault_pod" -- \
  env VAULT_TOKEN="$vault_token" \
  vault kv put "$vault_path" \
  "admin-password=$admin_password" \
  "postgres-admin-password=$postgres_admin_password" \
  "postgres-password=$postgres_password" \
  "grafana-client-secret=$grafana_client_secret" \
  "argocd-client-secret=$argocd_client_secret" \
  "sso-admin-user=$sso_admin_user" \
  "sso-admin-password=$sso_admin_password" >/dev/null

printf 'Keycloak secrets are seeded at %s.\n' "$vault_path"
printf 'SSO user: %s\n' "$sso_admin_user"
printf 'SSO password: %s\n' "$sso_admin_password"
