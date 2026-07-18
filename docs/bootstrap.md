# Bootstrap procedure

## 1. Host preparation

Edit `ansible/inventory/hosts.yml`, then:

```bash
cd ansible
ansible-playbook playbooks/site.yml
```

The generated kubeconfig is written to the repository root and ignored by Git.

## 2. Argo CD bootstrap

Install Argo CD CLI and export a GitHub token with repository administration access:

```bash
export GITHUB_TOKEN=...
python scripts/installer.py --config deploy/installer.toml
```

For a private repository, keep it private and let Argo CD create a deploy key.

## 3. Secrets

Install SOPS and age. Generate an age key and register its public key in `.sops.yaml`.
Store the private key in the cluster as `sops-age` in `argocd`.

Never commit plaintext credentials.

## 4. Platform ordering

Recommended enablement order:

1. namespaces;
2. cert-manager;
3. ClusterIssuer;
4. monitoring;
5. tracing;
6. data services;
7. CasinoShiz application chart.

## 5. Production readiness checklist

- Replace all `CHANGE_ME` values.
- Pin chart and image versions.
- Push immutable application images to GHCR.
- Configure resource requests and limits.
- Configure external backups.
- Test full restore onto a new VPS.
- Restrict Grafana and MinIO admin endpoints.
- Configure firewall for SSH, HTTP and HTTPS only.

## Local Argo CD bootstrap

```bash
python scripts/infra.py local create
python scripts/infra.py local argocd-bootstrap
```

The local root application deploys the data stack, observability, and the
CasinoShiz chart with `charts/casinoshiz/values-local.yaml`. Push application
images to the k3d registry with `python scripts/infra.py local image-push`.
