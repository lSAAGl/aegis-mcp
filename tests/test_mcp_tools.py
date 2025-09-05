import os

from mcp_server import audit_write, policy_get, require_approval


def test_policy_get_shape():
    p = policy_get()
    assert isinstance(p, dict)
    assert 'max_refund_cents' in p
    assert 'max_payment_link_cents' in p
    assert 'allow_tools' in p
    assert 'deny_tools' in p


def test_audit_write_returns_trace_and_ok():
    res = audit_write(action='pytest', tool='unit', ok=True, note='wf-40')
    assert isinstance(res, dict)
    assert res.get('ok') is True
    assert isinstance(res.get('trace_id'), str) and len(res['trace_id']) > 0
    assert isinstance(res.get('path'), str) and len(res['path']) > 0


def test_require_approval_two_phase():
    # Phase 1: pending
    r1 = require_approval('dry-wf40')
    assert r1.get('status') == 'pending'
    assert r1.get('approval_required') is True
    assert isinstance(r1.get('approval_id'), str)

    # Phase 2: approve using default code '123456' unless overridden
    code = os.environ.get('APPROVAL_CODE', '123456')
    r2 = require_approval('dry-wf40', approval_code=code)
    assert r2.get('status') in ('approved', 'denied')
    if r2['status'] == 'approved':
        assert r2.get('ok') is True
        assert isinstance(r2.get('trace_id'), str)
    else:
        # If user changed APPROVAL_CODE env, approval may be denied
        assert r2.get('ok') is False