import json
import os
import time
import uuid
from typing import Optional

from fastmcp import FastMCP

from src.app.audit import write as _audit_write
from src.app.enforcer import enforce as _enforce
from src.app.guard import evaluate as _guard_evaluate
from src.app.policy import load_policy

# Read approval code on each call fallback to default; we also keep a module-level
# default but do not cache file paths (fixes test isolation).
DEFAULT_APPROVAL_CODE = "123456"


def _approvals_path() -> str:
    return os.environ.get("APPROVALS_PATH", "approvals.log")


def _append_approval(entry: dict) -> dict:
    rec = dict(entry)
    rec["ts"] = int(time.time())
    path = _approvals_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec

# ---- Core functions (also exposed as MCP tools) ----

def policy_get() -> dict:
    """Return active policy dict (loaded from POLICY_PATH or defaults)."""
    return load_policy()


def audit_write(action: str, tool: Optional[str] = None, ok: Optional[bool] = None, note: Optional[str] = None) -> dict:
    """Append an audit event; returns {ok, trace_id, path}."""
    info = _audit_write({"action": action, "tool": tool, "ok": ok, "note": note})
    return {"ok": True, **info}


def require_approval(dry_run_id: str, approval_code: Optional[str] = None) -> dict:
    """Two-phase approval simulation.
    - Call without approval_code → records a PENDING approval and returns approval_required.
    - Call with correct code → records an APPROVED entry and returns ok=True.
    """
    provided = approval_code if approval_code is not None else ""
    correct_code = os.environ.get("APPROVAL_CODE", DEFAULT_APPROVAL_CODE)

    if not provided:
        # Phase 1: create pending record
        approval_id = str(uuid.uuid4())
        _append_approval({"status": "pending", "dry_run_id": dry_run_id, "approval_id": approval_id})
        return {
            "ok": False,
            "status": "pending",
            "approval_required": True,
            "approval_id": approval_id,
            "hint": "Call require_approval again with approval_code.",
            "code_set": False,
        }

    if provided == correct_code:
        # Approved
        approval_id = str(uuid.uuid4())
        rec = _append_approval({"status": "approved", "dry_run_id": dry_run_id, "approval_id": approval_id})
        audit = _audit_write({
            "action": "approval",
            "ok": True,
            "note": f"dry_run_id={dry_run_id}",
        })
        out = {"ok": True, "status": rec["status"], "approval_id": approval_id}
        out.update({"trace_id": audit.get("trace_id"), "audit_path": audit.get("path")})
        return out

    # Wrong code → denied
    approval_id = str(uuid.uuid4())
    rec = _append_approval({"status": "denied", "dry_run_id": dry_run_id, "approval_id": approval_id})
    return {"ok": False, "status": rec["status"], "approval_id": approval_id}

def guard_check(tool: str, amount_cents: Optional[int] = None, op: Optional[str] = None) -> dict:
    """Policy decision for a prospective tool call."""
    return _guard_evaluate(tool, amount_cents=amount_cents, op=op)


def firewall_enforce(tool: str, amount_cents: Optional[int] = None, op: Optional[str] = None, meta: Optional[dict] = None) -> dict:
    return _enforce(tool, amount_cents=amount_cents, op=op, meta=meta)


# ---- Create MCP server and register tools ----
mcp = FastMCP(
    "mcp-firewall",
    version="0.2.0",
    instructions="Guard tools for MCP: policy_get, audit_write, require_approval, guard_check, firewall_enforce",
)

mcp.tool(policy_get)
mcp.tool(audit_write)
mcp.tool(require_approval)
mcp.tool(guard_check)
mcp.tool(firewall_enforce)


if __name__ == "__main__":
    # Run as an MCP stdio server
    mcp.run()