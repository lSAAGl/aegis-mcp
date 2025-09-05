from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from typing_extensions import Literal


# ---------------------------
# Pydantic models (v2 schema)
# ---------------------------
class Rule(BaseModel):
    model_config = ConfigDict(extra='forbid')

    match: str = Field(..., description='Glob pattern for tool name')
    decision: Literal['allow', 'review', 'deny']
    cap_cents: Optional[int] = Field(default=None, description='Optional amount cap in cents')
    ops: Optional[List[str]] = Field(default=None, description='Optional list of allowed ops')
    reason: Optional[str] = None

    @field_validator('cap_cents')
    @classmethod
    def _cap_is_int_and_nonneg(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if not isinstance(v, int):
            raise TypeError('cap_cents must be int')
        if v < 0:
            raise ValueError('cap_cents must be >= 0')
        return v


class PolicyV2(BaseModel):
    model_config = ConfigDict(extra='forbid')

    version: int = Field(2, description='Must be 2')
    rules: List[Rule]

    @field_validator('version')
    @classmethod
    def _must_be_two(cls, v: int) -> int:
        if v != 2:
            raise ValueError('version must be 2')
        return v


# ---------------------------
# Migration (v1 -> v2)
# ---------------------------
# v1 keys: max_refund_cents, max_payment_link_cents, allow_tools, deny_tools
# Behavior: deny first, then allow (with caps when relevant), fallback review

_DEF_FALLBACK_REASON = 'migrated from v1: tools not explicitly allowed require approval'


def migrate_v1_to_v2(v1: Dict[str, Any]) -> Dict[str, Any]:
    v1 = dict(v1 or {})
    rules: List[Dict[str, Any]] = []

    # 1) Deny list first (highest precedence)
    for pat in v1.get('deny_tools', []) or []:
        rules.append({'match': pat, 'decision': 'deny', 'reason': 'v1 deny_tools'})

    # 2) Allow list (with optional caps)
    max_refund = v1.get('max_refund_cents')
    max_plink = v1.get('max_payment_link_cents')
    for pat in v1.get('allow_tools', []) or []:
        rule: Dict[str, Any] = {'match': pat, 'decision': 'allow'}
        # Add caps heuristically for common tools if available
        if pat.startswith('refunds') and isinstance(max_refund, int):
            rule['cap_cents'] = max_refund
            rule['ops'] = ['refund']
            rule['reason'] = 'v1 refunds cap'
        if pat.startswith('payment_links') and isinstance(max_plink, int):
            rule['cap_cents'] = max_plink
            rule['reason'] = 'v1 payment_links cap'
        rules.append(rule)

    # 3) Fallback to review (approval)
    rules.append({'match': '*', 'decision': 'review', 'reason': _DEF_FALLBACK_REASON})

    return {'version': 2, 'rules': rules}


# ---------------------------
# Validation entry-point
# ---------------------------

def validate_policy_input(policy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a supplied policy. Accepts v2 directly; migrates v1 in-memory first.
    Returns: { ok: bool, errors: [str], version: 2, migrated?: bool, notes?: [str] }
    """
    notes: List[str] = []
    migrated = False

    if isinstance(policy, dict) and policy.get('version') == 2:
        data = policy
    else:
        migrated = True
        data = migrate_v1_to_v2(policy or {})
        notes.append('Migrated legacy v1 policy to v2 for validation')

    try:
        PolicyV2.model_validate(data)
        return {'ok': True, 'errors': [], 'version': 2, 'migrated': migrated, 'notes': notes}
    except ValidationError as e:
        # Flatten errors into readable strings
        msgs: List[str] = []
        for err in e.errors():
            loc = '.'.join(str(x) for x in (err.get('loc') or []))
            msg = err.get('msg') or 'invalid'
            typ = err.get('type') or ''
            if loc:
                msgs.append(f"{loc}: {msg} ({typ})")
            else:
                msgs.append(msg)
        return {'ok': False, 'errors': msgs, 'version': 2, 'migrated': migrated, 'notes': notes}