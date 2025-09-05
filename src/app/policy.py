import os
from typing import Optional

import yaml

DEFAULTS = {
    "max_refund_cents": 0,
    "max_payment_link_cents": 0,
    "allow_tools": ["*"],
    "deny_tools": [],
}


def _coerce_policy(data: dict) -> dict:
    try:
        max_ref = int(data.get("max_refund_cents", DEFAULTS["max_refund_cents"]))
    except Exception:
        max_ref = DEFAULTS["max_refund_cents"]
    try:
        max_pl = int(data.get("max_payment_link_cents", DEFAULTS["max_payment_link_cents"]))
    except Exception:
        max_pl = DEFAULTS["max_payment_link_cents"]
    allow = data.get("allow_tools", DEFAULTS["allow_tools"]) or ["*"]
    deny = data.get("deny_tools", DEFAULTS["deny_tools"]) or []
    return {
        "path": data.get("_path"),
        "max_refund_cents": max_ref,
        "max_payment_link_cents": max_pl,
        "allow_tools": list(allow),
        "deny_tools": list(deny),
    }


def load_policy(path: Optional[str] = None) -> dict:
    """Load YAML policy from disk; return safe, typed dict with defaults if missing."""
    path = path or os.environ.get("POLICY_PATH", "policy.yml")
    if not os.path.exists(path):
        return _coerce_policy({"_path": path})
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}
        raw["_path"] = path
    
    # If this is a v2 policy, return it as-is (don't coerce to v1)
    if isinstance(raw, dict) and raw.get('version') == 2:
        return raw
    
    # Otherwise, coerce to v1 format for backward compatibility
    return _coerce_policy(raw)