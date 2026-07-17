# Bootstrap procedure

## 1. Host preparation

Edit `ansible/inventory/hosts.yml`, then:

```bash
cd ansible
ansible-playbook playbooks/site.yml
```

The generated kubeconfig is written to the repository root and ignored by Git.

## 2. Flux bootstrap

Install Flux CLI and export a GitHub token with repository administration access:

```bash
export GITHUB_TOKEN=...
flux bootstrap github   --owner=cpp20120   --repository=CasinoShiz.Infrastructure   --branch=main   --path=clusters/production   --personal
```

For a private repository, keep it private and let Flux create a deploy key.

## 3. Secrets

Install SOPS and age. Generate an age key and register its public key in `.sops.yaml`.
Store the private key in the cluster as `sops-age` in `flux-system`.

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
