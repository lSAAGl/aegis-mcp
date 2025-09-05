import json
import os

from mcp_server import audit_write, guard_check, policy_get, require_approval


def _print(label, obj):
    print(label, json.dumps(obj))


def main():
    # List available guard tools (static listing since we import directly)
    _print("TOOLS", ["policy_get", "audit_write", "require_approval", "guard_check"])

    # Policy snapshot
    _print("POLICY_GET", policy_get())

    # Audit
    _print("AUDIT_WRITE", audit_write(action="direct", tool="client", ok=True, note="wf-50+guard"))

    # Approval two-phase
    r1 = require_approval("dry-direct-guard")
    _print("APPROVAL_1", r1)
    code = os.environ.get("APPROVAL_CODE", "123456")
    r2 = require_approval("dry-direct-guard", approval_code=code)
    _print("APPROVAL_2", r2)

    # Guard checks
    _print("GUARD_refund_under", guard_check(tool="refunds.refund", amount_cents=12000, op="refund"))
    _print("GUARD_refund_over", guard_check(tool="refunds.refund", amount_cents=20000, op="refund"))
    _print("GUARD_users_export", guard_check(tool="users.export"))


if __name__ == "__main__":
    main()