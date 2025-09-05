import os, textwrap
import json
import pytest

# These tests exercise v2 policy evaluation through the existing guard.evaluate()
# without breaking v1 behavior.

V2_BASE = textwrap.dedent('''\
version: 2
rules:
  - match: "refunds.*"
    decision: allow
    cap_cents: 15000
    ops: ["refund"]
    reason: "Refunds ≤ $150 auto-approve"
  - match: "payment_links.create"
    decision: allow
    cap_cents: 25000
    reason: "Payment links ≤ $250 auto-approve"
  - match: "admin.*"
    decision: deny
    reason: "Admin operations disabled"
  - match: "*"
    decision: review
    reason: "Default: require approval"
''')


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


def test_v2_under_cap_allows(tmp_path, monkeypatch):
    path = _write(tmp_path, 'policy.yml', V2_BASE)
    monkeypatch.setenv('POLICY_PATH', path)

    from src.app.guard import evaluate
    res = evaluate('refunds.refund', amount_cents=12000, op='refund')
    assert res['allowed'] is True and res['approval_required'] is False


def test_v2_over_cap_requires_review(tmp_path, monkeypatch):
    path = _write(tmp_path, 'policy.yml', V2_BASE)
    monkeypatch.setenv('POLICY_PATH', path)

    from src.app.guard import evaluate
    res = evaluate('refunds.refund', amount_cents=20000, op='refund')
    assert res['allowed'] is False and res['approval_required'] is True
    assert any('cap' in r.lower() or 'exceed' in r.lower() for r in res['reasons'])


def test_v2_deny_has_no_approval(tmp_path, monkeypatch):
    path = _write(tmp_path, 'policy.yml', V2_BASE)
    monkeypatch.setenv('POLICY_PATH', path)

    from src.app.guard import evaluate
    res = evaluate('admin.nuke')
    assert res['allowed'] is False and res['approval_required'] is False


def test_v2_fallback_review(tmp_path, monkeypatch):
    path = _write(tmp_path, 'policy.yml', V2_BASE)
    monkeypatch.setenv('POLICY_PATH', path)

    from src.app.guard import evaluate
    res = evaluate('users.export')
    assert res['allowed'] is False and res['approval_required'] is True