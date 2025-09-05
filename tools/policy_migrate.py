#!/usr/bin/env python3
import sys
from pathlib import Path

import yaml

# Reuse server logic
from src.app.policy_v2 import migrate_v1_to_v2, validate_policy_input

USAGE = 'Usage: policy_migrate.py <path-to-v1-yaml | ->  # - reads stdin\n'

def _read_yaml(path: str):
    if path == '-' or path == '/dev/stdin':
        return yaml.safe_load(sys.stdin.read())
    return yaml.safe_load(Path(path).read_text(encoding='utf-8'))


def main():
    if len(sys.argv) != 2:
        sys.stderr.write(USAGE)
        sys.exit(2)
    src = sys.argv[1]
    raw = _read_yaml(src) or {}
    # If already v2, just validate and echo; else migrate
    if isinstance(raw, dict) and raw.get('version') == 2:
        res = validate_policy_input(raw)
        if not res['ok']:
            sys.stderr.write('\n'.join(res['errors']) + '\n')
            sys.exit(1)
        out = raw
    else:
        out = migrate_v1_to_v2(raw)
        res = validate_policy_input(out)
        if not res['ok']:
            sys.stderr.write('\n'.join(res['errors']) + '\n')
            sys.exit(1)
    sys.stdout.write(yaml.safe_dump(out))

if __name__ == '__main__':
    main()