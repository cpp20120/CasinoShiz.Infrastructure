# Vault secrets

Local Argo CD installs HashiCorp Vault in dev mode and External Secrets
Operator. The dev token is deliberately `root` and must never be used for a
production cluster. Existing SOPS secrets remain the bootstrap/fallback path;
this keeps the cluster recoverable before Vault has been initialized.

After Argo has synced `local-vault` and `local-external-secrets`, create a
Vault token Secret outside Git. It must be in the same namespace as the
`SecretStore`:

```sh
kubectl -n casinoshiz create secret generic vault-root-token \
  --from-literal=token=root
```

The checked-in `SecretStore` and `ExternalSecret` read KV v2 data from the
local Vault and materialize `casinoshiz-secrets-vault`:

```yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: vault
  namespace: casinoshiz
spec:
  provider:
    vault:
      server: http://vault.vault.svc.cluster.local:8200
      path: secret
      version: v2
      auth:
        tokenSecretRef:
          name: vault-root-token
          key: token
```

Seed the KV path from values that are already managed by SOPS. The helper
keeps the decoded payload on stdin and does not print it:

```sh
chmod +x scripts/vault-import-secret.sh
scripts/vault-import-secret.sh casinoshiz casinoshiz-secrets casinoshiz/app
```

The local application chart uses `casinoshiz-secrets-vault`. SOPS remains
available as the recovery/bootstrap source until Vault has been seeded.

For production use Raft storage, Kubernetes auth, a least-privilege Vault
policy, and an out-of-band unseal/root-token procedure. Do not copy the local
dev values into production.
