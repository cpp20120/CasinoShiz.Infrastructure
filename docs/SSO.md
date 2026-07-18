# SSO for platform UIs

Keycloak is the human identity provider for platform UIs. Vault remains the
machine-secret store: Keycloak bootstrap credentials, database passwords and
OIDC client secrets are read from Vault through External Secrets.

The local stack exposes Keycloak at:

```text
http://keycloak.casinoshiz.localhost:8080
```

The `casinoshiz` realm provisions clients for Grafana and Argo CD, groups
`platform-admins` and `platform-readonly`, and one bootstrap user. Grafana and
Argo keep their existing local admin fallback until SSO has been verified.

After Vault, External Secrets and the `local-vault-secrets` Argo application
are ready, seed the local-only credentials once:

```sh
chmod +x scripts/vault-seed-keycloak.sh
scripts/vault-seed-keycloak.sh
```

The script is idempotent and does not rotate existing values. Do not run it
against production: production should use a persistent Vault deployment,
Kubernetes auth, a least-privilege policy and an out-of-band unseal process.
The production Keycloak overlay must point its ExternalSecrets at that Vault
ClusterSecretStore before it is enabled.

The CasinoShiz Admin BFF is not switched automatically by this change because
it currently authenticates with its own web-token cookies. It needs native
OIDC validation (or a dedicated forward-auth proxy) before the two admin
hosts can use the Keycloak session directly.
