# SOPS and age

## One-time initialization

```bash
./scripts/sops-init.sh
```

This creates, when absent:

```text
~/.config/sops/age/keys.txt
```

and writes the derived public recipient into:

```text
.sops.yaml
```

The private identity must never be committed.

## Application Secret from an env file

```bash
ENV_FILE=../CasinoShiz/.env.production   go-task sops:app
```

Equivalent direct command:

```bash
./scripts/sops-create-app-secret.sh   ../CasinoShiz/.env.production
```

The plaintext env file is only an input. The generated tracked file is
encrypted immediately.

## GHCR pull Secret

```bash
export GHCR_USERNAME=cpp20120
read -rsp 'GHCR token: ' GHCR_TOKEN
export GHCR_TOKEN

./scripts/sops-create-ghcr-secret.sh

unset GHCR_TOKEN
```

Use a token with only the permissions needed to pull packages.

## Existing Secret manifests

```bash
./scripts/sops-encrypt.sh   data/data.secret.yaml   clusters/production/casinoshiz/casinoshiz.secret.yaml   clusters/production/casinoshiz/ghcr.secret.yaml
```

## Validation

```bash
./scripts/sops-check.sh
```

The check requires every tracked production `*.secret.yaml` file to:

- be a Kubernetes Secret;
- contain SOPS metadata;
- contain AES-GCM encrypted values;
- successfully authenticate and decrypt with the configured age identity.

It sends decrypted output to `/dev/null` and does not print plaintext.

## Flux bootstrap

The installer creates:

```text
namespace: flux-system
Secret: sops-age
key: age.agekey
```

Flux Kustomizations that include encrypted manifests require:

```yaml
spec:
  decryption:
    provider: sops
    secretRef:
      name: sops-age
```
