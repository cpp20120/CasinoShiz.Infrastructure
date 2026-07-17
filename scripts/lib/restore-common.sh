#!/usr/bin/env sh
set -eu

NAMESPACE="${NAMESPACE:-data}"
BACKUP_PVC="${BACKUP_PVC:-data-backups}"

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '==> %s\n' "$*"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

latest_backup_dir() {
  kind="$1"
  kubectl -n "$NAMESPACE" run "backup-lister-$$" \
    --restart=Never \
    --image=alpine:3.22 \
    --overrides="$(
      cat <<JSON
{
  "spec": {
    "containers": [{
      "name": "lister",
      "image": "alpine:3.22",
      "command": ["/bin/sh", "-ec", "find /backup/$kind -mindepth 1 -maxdepth 1 -type d -printf '%f\\n' | sort | tail -n 1"],
      "volumeMounts": [{"name": "backups", "mountPath": "/backup"}]
    }],
    "volumes": [{"name": "backups", "persistentVolumeClaim": {"claimName": "$BACKUP_PVC"}}]
  }
}
JSON
    )" >/dev/null

  kubectl -n "$NAMESPACE" wait \
    --for=jsonpath='{.status.phase}'=Succeeded \
    "pod/backup-lister-$$" \
    --timeout=90s >/dev/null

  result="$(kubectl -n "$NAMESPACE" logs "pod/backup-lister-$$")"
  kubectl -n "$NAMESPACE" delete pod "backup-lister-$$" --wait=false >/dev/null 2>&1 || true
  [ -n "$result" ] || die "no backup directories found for $kind"
  printf '%s\n' "$result"
}

wait_job() {
  job="$1"
  timeout="${2:-600s}"
  kubectl -n "$NAMESPACE" wait \
    --for=condition=complete \
    "job/$job" \
    --timeout="$timeout" || {
      kubectl -n "$NAMESPACE" logs "job/$job" --all-containers=true || true
      return 1
    }
  kubectl -n "$NAMESPACE" logs "job/$job" --all-containers=true
}
