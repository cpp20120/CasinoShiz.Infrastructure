# Taskfile merge

Add this task to the existing `validate` task:

```yaml
  validate:
    deps:
      - lint
      - render:chart
      - render:cluster
    cmds:
      - task: secrets:check
      - ./scripts/sops-check.sh
```

Or copy the tasks from `Taskfile.sops.yml` into the main `Taskfile.yml`.

The old regex-only `secrets:check` may remain as a defense-in-depth scanner.
The SOPS check is authoritative for files named `*.secret.yaml`.
