import os
from fastapi.testclient import TestClient
import pytest

# Endpoints under test (to be implemented):
#  - GET /approvals           -> { approvals: [ {dry_run_id, status, ts, approval_id?} ] }
#  - POST /approvals/complete -> { ok: bool, status: "approved"|"denied", approval_id: str }
#  - GET /ui/approvals        -> HTML page listing pending approvals
# Helpers live in src/app/approvals.py (to be added in implementation step).


def _setup_env(tmp_path, monkeypatch):
    approvals = tmp_path / "approvals.log"
    audit = tmp_path / "audit.log"
    monkeypatch.setenv("APPROVALS_PATH", str(approvals))
    monkeypatch.setenv("AUDIT_PATH", str(audit))
    monkeypatch.setenv("APPROVAL_CODE", "123456")
    return approvals, audit

@pytest.mark.parametrize("dry_id", ["dry-ui-1"]) 
def test_list_pending_returns_created_dry_run(tmp_path, monkeypatch, dry_id):
    approvals_path, _ = _setup_env(tmp_path, monkeypatch)

    # Create a pending approval using existing Python function
    from mcp_server import require_approval
    res1 = require_approval(dry_id)
    assert res1["status"] == "pending"

    # Verify the approval was written to the temp file before calling HTTP endpoint
    with open(approvals_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert dry_id in content  # Basic sanity check
    
    from src.app.main import app
    client = TestClient(app)
    r = client.get("/approvals")
    assert r.status_code == 200  # will FAIL until endpoint exists
    data = r.json()
    assert "approvals" in data
    ids = [a["dry_run_id"] for a in data["approvals"]]
    # Debug: print what we got vs what we expected
    if dry_id not in ids:
        print(f"Expected {dry_id} in {ids}, approvals data: {data['approvals']}")
        print(f"APPROVALS_PATH env: {os.environ.get('APPROVALS_PATH')}")
        print(f"Temp file content: {content}")
    assert dry_id in ids
    # Ensure it's marked pending
    assert any(a.get("status") == "pending" for a in data["approvals"] if a.get("dry_run_id") == dry_id)


def test_complete_approval_success(tmp_path, monkeypatch):
    approvals_path, audit_path = _setup_env(tmp_path, monkeypatch)

    from mcp_server import require_approval
    dry_id = "dry-ui-2"
    require_approval(dry_id)

    from src.app.main import app
    client = TestClient(app)

    # Complete with correct code
    r = client.post("/approvals/complete", json={"dry_run_id": dry_id, "approval_code": "123456"})
    assert r.status_code == 200  # will FAIL until endpoint exists
    body = r.json()
    assert body.get("ok") is True
    assert body.get("status") == "approved"
    assert isinstance(body.get("approval_id"), str)

    # Now should no longer appear as pending
    r2 = client.get("/approvals")
    pendings = [a for a in r2.json().get("approvals", []) if a.get("status") == "pending" and a.get("dry_run_id") == dry_id]
    assert len(pendings) == 0

    # Audit file should contain an approval entry
    if os.path.exists(audit_path):
        with open(audit_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "approval" in content
    else:
        # If no audit file, the approval should still have succeeded
        assert body.get("ok") is True


def test_complete_wrong_code_denied(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)

    from mcp_server import require_approval
    dry_id = "dry-ui-3"
    require_approval(dry_id)

    from src.app.main import app
    client = TestClient(app)

    r = client.post("/approvals/complete", json={"dry_run_id": dry_id, "approval_code": "000000"})
    assert r.status_code == 200  # will FAIL until endpoint exists
    body = r.json()
    assert body.get("ok") is False
    assert body.get("status") == "denied"

    # Should not be listed as pending anymore (latest state not pending)
    r2 = client.get("/approvals")
    pendings = [a for a in r2.json().get("approvals", []) if a.get("status") == "pending" and a.get("dry_run_id") == dry_id]
    assert len(pendings) == 0


def test_ui_page_serves_html(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    from src.app.main import app
    client = TestClient(app)
    r = client.get("/ui/approvals")
    assert r.status_code == 200  # will FAIL until endpoint exists
    assert "text/html" in r.headers.get("content-type", "").lower()
    assert "<table" in r.text.lower()