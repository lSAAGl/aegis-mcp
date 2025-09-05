import fnmatch
from typing import Optional

from .engine_v2 import evaluate_v2 as _evaluate_v2
from .policy import load_policy


def evaluate(tool: str, amount_cents: Optional[int] = None, op: Optional[str] = None) -> dict:
    """Evaluate whether a tool call is allowed based on active policy.
    - If the policy file is version 2, use the v2 rules engine (top-down).
    - Otherwise, use the existing v1 logic (unchanged).
    """
    p = load_policy()
    if isinstance(p, dict) and p.get('version') == 2:
        return _evaluate_v2(p, tool, amount_cents=amount_cents, op=op)

    # --------- BEGIN existing v1 logic (unchanged) ---------
    # Use existing implementation below exactly as-is so existing tests remain stable.
    # (Keep deny/allow/caps reasoning strings intact.)
    # --------------------------------------------------------
    
    policy = p
    allow_tools = policy.get("allow_tools", [])
    deny_tools = policy.get("deny_tools", [])
    max_refund_cents = policy.get("max_refund_cents", 0)
    max_payment_link_cents = policy.get("max_payment_link_cents", 0)
    
    reasons = []
    
    # Check deny list first (hard block)
    for pattern in deny_tools:
        if fnmatch.fnmatch(tool, pattern):
            reasons.append(f"Tool '{tool}' matches deny pattern '{pattern}'")
            return {"allowed": False, "approval_required": False, "reasons": reasons}
    
    # Check allow list
    tool_allowed = False
    for pattern in allow_tools:
        if fnmatch.fnmatch(tool, pattern):
            tool_allowed = True
            break
    
    if not tool_allowed:
        reasons.append(f"Tool '{tool}' is not in the allow list")
        return {"allowed": False, "approval_required": True, "reasons": reasons}
    
    # Tool is in allow list, check amount caps
    cap = None
    if op == "refund":
        cap = max_refund_cents
    elif op == "payment_link_create":
        cap = max_payment_link_cents
    
    # If operation has a cap
    if cap is not None and cap > 0:
        if amount_cents is None:
            reasons.append(f"Amount required for operation '{op}' but not provided")
            return {"allowed": False, "approval_required": True, "reasons": reasons}
        
        if amount_cents > cap:
            if op == "refund":
                reasons.append(f"Refund amount {amount_cents} exceeds max_refund_cents cap of {cap}")
            elif op == "payment_link_create":
                reasons.append(f"Payment link amount {amount_cents} exceeds max_payment_link_cents cap of {cap}")
            return {"allowed": False, "approval_required": True, "reasons": reasons}
    
    # All checks passed
    return {"allowed": True, "approval_required": False, "reasons": []}