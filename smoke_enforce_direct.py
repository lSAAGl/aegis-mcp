import json

from mcp_server import firewall_enforce


def _p(label, obj):
    print(label, json.dumps(obj))


def main():
    # 1) Allowed: refund under cap (15000 default)
    under = firewall_enforce(tool="refunds.refund", amount_cents=12000, op="refund")
    _p("ENFORCE_under", under)

    # 2) Pending: refund over cap -> approval_required + approval_id
    over = firewall_enforce(tool="refunds.refund", amount_cents=20000, op="refund")
    _p("ENFORCE_over", over)

    # 3) Approval required: tool not in allow list by default
    users_export = firewall_enforce(tool="users.export")
    _p("ENFORCE_users_export", users_export)

    print("\nNote: To see a hard 'blocked' status, put a glob in deny_tools (policy.yml) that matches your tool.")


if __name__ == "__main__":
    main()