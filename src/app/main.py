from typing import Optional, List, Dict, Any
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .policy import load_policy
from .audit import write as audit_write
from .guard import evaluate as guard_evaluate
from .approvals import list_approvals, complete_approval
from .enforcer import enforce as guard_enforce
from .policy_v2 import validate_policy_input, migrate_v1_to_v2

app = FastAPI(title="MCP Firewall MVP")


class HealthResponse(BaseModel):
    status: str

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")

@app.get("/policy")
def get_policy() -> dict:
    """Return the current policy (safe subset) and its source path."""
    return {"policy": load_policy()}


class AuditEvent(BaseModel):
    action: str
    tool: Optional[str] = None
    ok: Optional[bool] = None
    note: Optional[str] = None


class AuditWriteResult(BaseModel):
    ok: bool
    trace_id: str
    path: str

@app.post("/audit", response_model=AuditWriteResult, status_code=201)
def post_audit(event: AuditEvent) -> AuditWriteResult:
    info = audit_write(event.dict(exclude_none=True))
    return AuditWriteResult(ok=True, **info)


# ---- Guard check HTTP endpoint ----
class GuardRequest(BaseModel):
    tool: str
    amount_cents: Optional[int] = None
    op: Optional[str] = None


class GuardResult(BaseModel):
    allowed: bool
    approval_required: bool
    reasons: List[str] = []


@app.post("/guard/check", response_model=GuardResult)
def guard_check_http(req: GuardRequest) -> GuardResult:
    res = guard_evaluate(req.tool, amount_cents=req.amount_cents, op=req.op)
    return GuardResult(**res)


# ---- Approvals JSON endpoints ----
@app.get("/approvals")
def approvals_list() -> dict:
    # Use environment variable to pick up test overrides
    import os
    approvals_path = os.environ.get("APPROVALS_PATH")
    return {"approvals": list_approvals(approvals_path)}


class ApprovalsCompleteRequest(BaseModel):
    dry_run_id: str
    approval_code: str


@app.post("/approvals/complete")
def approvals_complete(req: ApprovalsCompleteRequest) -> dict:
    res = complete_approval(req.dry_run_id, req.approval_code)
    # Return keys asserted in tests
    return {
        "ok": bool(res.get("ok")),
        "status": res.get("status"),
        "approval_id": res.get("approval_id"),
    }


# ---- Approvals HTML UI ----
@app.get("/ui/approvals", response_class=HTMLResponse)
def approvals_ui() -> str:
    # Use environment variable to pick up test overrides
    import os
    approvals_path = os.environ.get("APPROVALS_PATH")
    rows = []
    for r in list_approvals(approvals_path):
        did = r.get("dry_run_id", "")
        rows.append(
            f"<tr>"
            f"<td>{did}</td>"
            f"<td>{r.get('status','')}</td>"
            f"<td>{r.get('ts','')}</td>"
            f"<td>{r.get('approval_id','')}</td>"
            f"<td>"
            f"<input id='code-{did}' placeholder='code' />"
            f"<button onclick=\"fetch('/approvals/complete',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{dry_run_id:'{did}',approval_code:document.getElementById('code-{did}').value}})}}).then(()=>location.reload())\">Complete</button>"
            f"</td>"
            f"</tr>"
        )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><title>Approvals</title></head>"
        "<body><h1>Approvals</h1>"
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<thead><tr><th>dry_run_id</th><th>status</th><th>ts</th><th>approval_id</th><th>complete</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
        "</body></html>"
    )
    return html


# ---- Firewall Enforce HTTP endpoint ----
class EnforceRequest(BaseModel):
    tool: str
    amount_cents: Optional[int] = None
    op: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class EnforceResult(BaseModel):
    allowed: bool
    approval_required: bool
    status: str
    reasons: List[str] = []
    approval_id: Optional[str] = None


@app.post("/guard/enforce", response_model=EnforceResult)
def guard_enforce_http(req: EnforceRequest) -> EnforceResult:
    res = guard_enforce(req.tool, amount_cents=req.amount_cents, op=req.op, meta=req.meta)
    return EnforceResult(**res)


# ---- Policy Validation HTTP endpoint ----
class PolicyValidateRequest(BaseModel):
    policy: Dict[str, Any]

class PolicyValidateResult(BaseModel):
    ok: bool
    errors: List[str] = []
    version: int
    migrated: Optional[bool] = None
    notes: Optional[List[str]] = None

@app.post('/policy/validate', response_model=PolicyValidateResult)
def policy_validate(req: PolicyValidateRequest) -> PolicyValidateResult:
    res = validate_policy_input(req.policy)
    return PolicyValidateResult(**res)


# ---- Policy Effective/Migration HTTP endpoints ----
@app.get('/policy/effective')
def policy_effective() -> dict:
    # Return the policy the server is currently using (v2 preserved, v1 coerced)
    p = load_policy()
    # drop internal helper keys like '_path' if present
    if isinstance(p, dict) and '_path' in p:
        p = {k: v for k, v in p.items() if k != '_path'}
    return p


class PolicyMigrateRequest(BaseModel):
    policy: Dict[str, Any]

class PolicyMigrateResult(BaseModel):
    ok: bool
    version: int
    policy: Dict[str, Any]

@app.post('/policy/migrate', response_model=PolicyMigrateResult)
def policy_migrate(req: PolicyMigrateRequest) -> PolicyMigrateResult:
    raw = req.policy or {}
    if isinstance(raw, dict) and raw.get('version') == 2:
        v2 = raw
    else:
        v2 = migrate_v1_to_v2(raw)
    return PolicyMigrateResult(ok=True, version=2, policy=v2)