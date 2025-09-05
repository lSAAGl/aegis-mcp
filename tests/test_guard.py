import importlib
import os
import json
import types
import pytest

# We will call: evaluate(tool, amount_cents=None, op=None) -> {allowed, approval_required, reasons: [str]}
# Semantics under default policy.yml in repo:
# - allow_tools: ["refunds.*", "payment_links.create"], deny_tools: []
# - caps: max_refund_cents=15000, max_payment_link_cents=25000
# Rules:
#   * If tool matches deny_tools → allowed=False, approval_required=False (hard block)
#   * Else if tool matches allow_tools:
#       - If op has a cap and amount_cents is None → allowed=False, approval_required=True (needs approval)
#       - If amount_cents <= cap → allowed=True, approval_required=False
#       - If amount_cents > cap → allowed=False, approval_required=True
#   * Else (not in allow list) → allowed=False, approval_required=True (needs approval)


def _reload_guard():
    # Helper to reload guard module after env changes
    if "src.app.guard" in list(sys.modules.keys()):
        import sys
        sys.modules.pop("src.app.guard", None)
    import src.app.guard as guard  # noqa: F401
    importlib.reload(guard)
    return guard


def test_refund_under_cap_allowed(monkeypatch):
    # Uses repo policy.yml by default
    from src.app import __init__ as _  # ensure package importable
    import src.app.guard as guard  # will fail until implemented
    result = guard.evaluate("refunds.refund", amount_cents=12000, op="refund")
    assert result["allowed"] is True
    assert result["approval_required"] is False
    assert result.get("reasons") == []


def test_refund_over_cap_requires_approval():
    import src.app.guard as guard
    result = guard.evaluate("refunds.refund", amount_cents=20000, op="refund")
    assert result["allowed"] is False
    assert result["approval_required"] is True
    assert any("max_refund_cents" in r for r in result["reasons"])  # explanatory reason


def test_payment_link_over_cap_requires_approval():
    import src.app.guard as guard
    result = guard.evaluate("payment_links.create", amount_cents=30000, op="payment_link_create")
    assert result["allowed"] is False
    assert result["approval_required"] is True
    assert any("max_payment_link_cents" in r for r in result["reasons"])  # explanatory reason


def test_tool_not_in_allow_list_requires_approval():
    import src.app.guard as guard
    result = guard.evaluate("users.export")
    assert result["allowed"] is False
    assert result["approval_required"] is True
    assert any("allow" in r.lower() for r in result["reasons"])  # explain allow list


def test_deny_list_blocks_without_approval(tmp_path, monkeypatch):
    # Create a temp policy that denies admin.* explicitly
    p = tmp_path / "policy.yml"
    p.write_text(json.dumps({
        "allow_tools": ["*"],
        "deny_tools": ["admin.*"],
        "max_refund_cents": 10_000_000,
        "max_payment_link_cents": 10_000_000
    }))
    monkeypatch.setenv("POLICY_PATH", str(p))
    import importlib, sys
    sys.modules.pop("src.app.guard", None)
    import src.app.guard as guard
    importlib.reload(guard)

    res = guard.evaluate("admin.reset_db")
    assert res["allowed"] is False
    assert res["approval_required"] is False  # hard block
    assert any("deny" in r.lower() for r in res["reasons"])  # explain deny list


def test_missing_amount_for_capped_op_requires_approval():
    import src.app.guard as guard
    res = guard.evaluate("refunds.refund", amount_cents=None, op="refund")
    assert res["allowed"] is False
    assert res["approval_required"] is True
    assert any("amount" in r.lower() for r in res["reasons"])  # explain missing amount