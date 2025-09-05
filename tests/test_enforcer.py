import os, json
from fastapi.testclient import TestClient
import pytest

# These tests define the desired behavior for a single-call enforcement entry point
# that combines: (1) policy evaluation, (2) audit logging, and (3) approval creation when required.
# Endpoint under test (to be implemented): POST /guard/enforce
# Expected response shape: {allowed: bool, approval_required: bool, status: str, reasons: list[str], approval_id?: str}
# Status semantics:
#   - 'allowed'  → request permitted immediately (no approval)
#   - 'pending'  → approval required (a pending record must be created in approvals.log)
#   - 'blocked'  → deny-list or hard block (no approval requested)

@pytest.fixture(autouse=True)
def _isolation(tmp_path, monkeypatch):
    # Per-test isolated files
    monkeypatch.setenv("APPROVALS_PATH", str(tmp_path / "approvals.log"))
    monkeypatch.setenv("AUDIT_PATH", str(tmp_path / "audit.log"))
    # Do NOT set POLICY_PATH here so defaults from policy.yml apply,
    # except for the deny-list test which writes its own policy.
    yield


def _client():
    from src.app.main import app
    return TestClient(app)


def test_enforce_under_cap_allows_no_approval():
    # refunds.refund under default cap (15000) should be allowed without approval
    client = _client()
    resp = client.post(
        "/guard/enforce",
        json={"tool": "refunds.refund", "amount_cents": 12000, "op": "refund", "meta": {"who": "test"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed"] is True
    assert body["approval_required"] is False
    assert body["status"] == "allowed"
    assert isinstance(body.get("reasons", []), list)

    # audit.log should receive an entry (action like 'enforce')
    audit_path = os.environ["AUDIT_PATH"]
    assert os.path.exists(audit_path)
    with open(audit_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "enforce" in content  # minimal side-effect assertion


def test_enforce_over_cap_creates_pending_and_approval_id():
    # refunds.refund over default cap (15000) should require approval (pending)
    client = _client()
    resp = client.post(
        "/guard/enforce",
        json={"tool": "refunds.refund", "amount_cents": 20000, "op": "refund"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed"] is False
    assert body["approval_required"] is True
    assert body["status"] == "pending"
    assert isinstance(body.get("reasons", []), list)
    assert "approval_id" in body and isinstance(body["approval_id"], str) and body["approval_id"]

    # approvals.log should contain a pending record with that approval_id
    approvals_path = os.environ["APPROVALS_PATH"]
    assert os.path.exists(approvals_path)
    with open(approvals_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert any("\"status\": \"pending\"" in ln for ln in lines)
    assert any(body["approval_id"] in ln for ln in lines)


def test_enforce_denylist_blocks_without_approval(tmp_path, monkeypatch):
    # Provide a policy that denies admin.*
    policy_yaml = tmp_path / "policy_deny.yml"
    policy_yaml.write_text(
        """
max_refund_cents: 15000
max_payment_link_cents: 25000
allow_tools:
  - "refunds.*"
  - "payment_links.create"
deny_tools:
  - "admin.*"
""".strip()
    )
    monkeypatch.setenv("POLICY_PATH", str(policy_yaml))

    client = _client()
    resp = client.post(
        "/guard/enforce",
        json={"tool": "admin.nuke", "op": "admin_action"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed"] is False
    assert body["approval_required"] is False
    assert body["status"] == "blocked"
    assert any("deny" in r.lower() or "not allowed" in r.lower() for r in body.get("reasons", []))

    # No pending approval should be created in this case
    approvals_path = os.environ["APPROVALS_PATH"]
    if os.path.exists(approvals_path):
        with open(approvals_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "\"status\": \"pending\"" not in content