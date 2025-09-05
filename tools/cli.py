#!/usr/bin/env python3
"""
Tiny helper CLI for local ops (validate/migrate). Keeps parity with HTTP endpoints.
Examples:
  python tools/cli.py validate examples/policy_v2.yml
  python tools/cli.py migrate policy.yml > policy.v2.yml
"""
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

from src.app.policy_v2 import migrate_v1_to_v2, validate_policy_input


def _read_yaml(p: str) -> Dict[str, Any]:
    if p == '-' or p == '/dev/stdin':
        return yaml.safe_load(sys.stdin.read()) or {}
    return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}

def main() -> int:
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: cli.py <validate|migrate> <path|->\n")
        return 2
    cmd, path = sys.argv[1], sys.argv[2]
    data = _read_yaml(path)
    if cmd == 'validate':
        res = validate_policy_input(data)
        if not res['ok']:
            for e in res['errors']:
                sys.stderr.write(e + "\n")
            return 1
        # echo validated (and migrated if needed) normalized policy
        sys.stdout.write(yaml.safe_dump(data if data.get('version') == 2 else migrate_v1_to_v2(data)))
        return 0
    if cmd == 'migrate':
        out = data if data.get('version') == 2 else migrate_v1_to_v2(data)
        res = validate_policy_input(out)
        if not res['ok']:
            for e in res['errors']:
                sys.stderr.write(e + "\n")
            return 1
        sys.stdout.write(yaml.safe_dump(out))
        return 0
    sys.stderr.write("Unknown command. Use validate|migrate.\n")
    return 2

if __name__ == '__main__':
    raise SystemExit(main())