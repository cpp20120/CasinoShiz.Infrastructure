#!/usr/bin/env python3
from pathlib import Path

root = Path.cwd()
values = root / 'argocd' / 'values.yaml'
infra = root / 'scripts' / 'infra.py'
local_values = root / 'argocd' / 'values-local.yaml'

for path in (values, infra):
    if not path.is_file():
        raise SystemExit(f'Run from repository root; missing: {path}')

text = values.read_text()
if '    - name: cmp-tmp\n      emptyDir: {}\n' not in text:
    anchor = '    - name: custom-tools\n      emptyDir: {}\n'
    if anchor not in text:
        raise SystemExit('Cannot find repoServer custom-tools volume in argocd/values.yaml')
    text = text.replace(anchor, anchor + '    - name: cmp-tmp\n      emptyDir: {}\n', 1)

text = text.replace(
    'image: quay.io/argoproj/argocd:v3.1.7',
    'image: quay.io/argoproj/argocd:v3.4.5',
)
values.write_text(text)

local_values.write_text('''global:\n  domain: argocd.casinoshiz.localhost\n\nserver:\n  ingress:\n    enabled: false\n    hostname: ""\n    tls: false\n    annotations: {}\n''')

text = infra.read_text()
marker = '--values argocd/values-local.yaml'
if marker not in text:
    needle = '--values argocd/values.yaml ' + ('\\' * 3) + 'n  --wait --timeout 15m'
    replacement = (
        '--values argocd/values.yaml ' + ('\\' * 3) + 'n'
        '  --values argocd/values-local.yaml ' + ('\\' * 3) + 'n'
        '  --wait --timeout 15m'
    )
    if needle not in text:
        raise SystemExit('Cannot find local Helm bootstrap command in scripts/infra.py')
    text = text.replace(needle, replacement, 1)
    infra.write_text(text)

print('Fixed:')
print('  argocd/values.yaml: added cmp-tmp volume')
print('  argocd/values-local.yaml: disabled local ingress')
print('  scripts/infra.py: added local values override')