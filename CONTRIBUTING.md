# Contributing

## Validation

Run before committing:

```bash
go-task clean
go-task validate
go-task placeholders
```

## Change policy

- Keep host provisioning in Ansible.
- Keep in-cluster resources declarative and Flux-managed.
- Do not use manual `kubectl apply` as the permanent source of truth.
- Do not add plaintext secrets.
- Pin production application images.
- Document backup and restore implications for stateful changes.

## Commit structure

Prefer focused commits, for example:

```text
add PostgreSQL backup alert rules
update Tempo retention
fix Redis readiness probe
```
