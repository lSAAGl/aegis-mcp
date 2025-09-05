import json
import os
import time
import uuid
from typing import Any, Dict, Optional

from .audit import write as audit_write
from .guard import evaluate as guard_evaluate


def _approvals_path() -> str:
    return os.environ.get("APPROVALS_PATH", "approvals.log")


def _append_approval(entry: Dict[str, Any]) -> Dict[str, Any]:
    rec = dict(entry)
    rec["ts"] = int(time.time())
    path = _approvals_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def enforce(
    tool: str,
    amount_cents: Optional[int] = None,
    op: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Unified firewall decision:
      1) Run policy evaluation
      2) Always write an audit 'enforce' entry
      3) If approval required, create a pending record and return approval_id

    Returns: {allowed: bool, approval_required: bool, status: str, reasons: [str], approval_id?: str}
    Status: 'allowed' | 'pending' | 'blocked'
    """
    res = guard_evaluate(tool, amount_cents=amount_cents, op=op)
    reasons = list(res.get("reasons", []))

    # Hard block (deny-list)
    if not res.get("allowed") and not res.get("approval_required"):
        audit_write({
            "action": "enforce",
            "ok": False,
            "tool": tool,
            "op": op,
            "amount_cents": amount_cents,
            "status": "blocked",
        })
        return {
            "allowed": False,
            "approval_required": False,
            "status": "blocked",
            "reasons": reasons,
        }

    # Allowed immediately
    if res.get("allowed") and not res.get("approval_required"):
        audit_write({
            "action": "enforce",
            "ok": True,
            "tool": tool,
            "op": op,
            "amount_cents": amount_cents,
            "status": "allowed",
        })
        return {
            "allowed": True,
            "approval_required": False,
            "status": "allowed",
            "reasons": reasons,
        }

    # Approval required → create pending approval
    dry_run_id = None
    if isinstance(meta, dict):
        dry_run_id = meta.get("dry_run_id")
    if not dry_run_id:
        dry_run_id = f"enf-{uuid.uuid4()}"

    approval_id = str(uuid.uuid4())
    _append_approval({
        "status": "pending",
        "dry_run_id": dry_run_id,
        "approval_id": approval_id,
    })

    audit_write({
        "action": "enforce",
        "ok": False,
        "tool": tool,
        "op": op,
        "amount_cents": amount_cents,
        "status": "pending",
        "note": f"dry_run_id={dry_run_id} approval_id={approval_id}",
    })

    return {
        "allowed": False,
        "approval_required": True,
        "status": "pending",
        "reasons": reasons,
        "approval_id": approval_id,
    }