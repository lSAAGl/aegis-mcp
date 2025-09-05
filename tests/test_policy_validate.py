import pytest
from fastapi.testclient import TestClient

from src.app.main import app

client = TestClient(app)

# The endpoint under test (to be implemented):
#   POST /policy/validate  -> { ok: bool, errors: [str], version: int, migrated?: bool }
# It validates a supplied policy document (v2 preferred, v1 accepted via in-memory migration).

VALID_V2 = {
    "version": 2,
    "rules": [
        {"match": "refunds.*", "decision": "allow", "cap_cents": 15000, "ops": ["refund"], "reason": "ok"},
        {"match": "payment_links.create", "decision": "allow", "cap_cents": 25000},
        {"match": "*", "decision": "review", "reason": "fallback"},
    ],
}

V1_LEGACY = {
    "max_refund_cents": 15000,
    "max_payment_link_cents": 25000,
    "allow_tools": ["refunds.*", "payment_links.create"],
    "deny_tools": [],
}

INVALID_DECISION = {
    "version": 2,
    "rules": [
        {"match": "refunds.*", "decision": "approve"},
    ],
}

INVALID_CAP_TYPE = {
    "version": 2,
    "rules": [
        {"match": "refunds.*", "decision": "allow", "cap_cents": "five"},
    ],
}

MISSING_MATCH = {
    "version": 2,
    "rules": [
        {"decision": "review"},
    ],
}

UNKNOWN_FIELD = {
    "version": 2,
    "rules": [
        {"match": "*", "decision": "review", "caps_cents": 1},
    ],
}


def post_validate(policy: dict):
    return client.post(
        "/policy/validate",
        json={"policy": policy},
        headers={"content-type": "application/json"},
    )


def test_validate_accepts_valid_v2():
    r = post_validate(VALID_V2)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("errors") == []
    assert body.get("version") == 2


def test_validate_migrates_v1_to_v2():
    r = post_validate(V1_LEGACY)
    assert r.status_code == 200
    body = r.json()
    # v1 should be accepted via migration, marked migrated, and surfaced as version 2
    assert body.get("ok") is True
    assert body.get("version") == 2
    assert body.get("migrated") is True
    # Helpful note or reason should be included (string list allowed)
    notes = body.get("notes") or []
    assert any("migrat" in s.lower() for s in notes)


def test_validate_rejects_bad_decision_value():
    r = post_validate(INVALID_DECISION)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is False
    errs = "\n".join(body.get("errors") or [])
    assert "decision" in errs and ("allow" in errs and "deny" in errs and "review" in errs)


def test_validate_rejects_non_int_cap():
    r = post_validate(INVALID_CAP_TYPE)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is False
    errs = "\n".join(body.get("errors") or [])
    assert "cap_cents" in errs and ("int" in errs or "integer" in errs)


def test_validate_requires_match_field():
    r = post_validate(MISSING_MATCH)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is False
    errs = "\n".join(body.get("errors") or [])
    assert "match" in errs


def test_validate_flags_unknown_fields():
    r = post_validate(UNKNOWN_FIELD)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is False
    errs = "\n".join(body.get("errors") or [])
    # should mention the bad key name 'caps_cents' or say unknown/extra fields
    assert ("caps_cents" in errs) or ("unknown" in errs.lower()) or ("extra" in errs.lower())