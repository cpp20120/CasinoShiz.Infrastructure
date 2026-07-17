#!/usr/bin/env bash
set -euo pipefail

required=(git helm kustomize kubectl go-task ansible-playbook)
missing=()

for tool in "${required[@]}"; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    missing+=("$tool")
  fi
done

if ((${#missing[@]} > 0)); then
  printf 'Missing required tools: %s\n' "${missing[*]}" >&2
  exit 1
fi

if [[ ! -f Taskfile.yml ]]; then
  echo "Run this script from the repository root." >&2
  exit 1
fi

echo "Validating repository..."
go-task clean
go-task validate

echo "Checking unresolved placeholders..."
placeholders="$(git grep -n CHANGE_ME || true)"
if [[ -n "$placeholders" ]]; then
  printf '%s\n' "$placeholders"
  echo "Unresolved CHANGE_ME values remain." >&2
  exit 1
fi

echo "Checking repository state..."
if [[ -n "$(git status --porcelain)" ]]; then
  git status --short
  echo "Working tree is not clean." >&2
  exit 1
fi

echo "Checking Kubernetes access..."
kubectl version --client
kubectl cluster-info
kubectl get nodes

echo "Preflight passed."
