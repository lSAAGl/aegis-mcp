import fnmatch
from typing import Any, Dict, List, Optional

# Evaluate a v2 policy (already validated or trusted input)
# Returns {allowed: bool, approval_required: bool, reasons: [str]}

def evaluate_v2(policy: Dict[str, Any], tool: str, amount_cents: Optional[int] = None, op: Optional[str] = None) -> Dict[str, Any]:
    rules: List[Dict[str, Any]] = list(policy.get('rules') or [])

    for rule in rules:
        pat = rule.get('match')
        if not pat:
            continue
        if not fnmatch.fnmatch(tool, pat):
            continue

        decision = rule.get('decision')
        reason = rule.get('reason')
        cap = rule.get('cap_cents')
        ops = rule.get('ops')  # None or list[str]

        if decision == 'deny':
            return {
                'allowed': False,
                'approval_required': False,
                'reasons': [reason or f"Denied by rule for '{pat}'"],
            }

        if decision == 'allow':
            # Cap escalation only applies to allow rules
            if cap is not None:
                applies = True if not ops else (op in ops if op is not None else False)
                if applies and (amount_cents is not None) and (amount_cents > int(cap)):
                    return {
                        'allowed': False,
                        'approval_required': True,
                        'reasons': [
                            f"Amount {amount_cents} exceeds cap {cap} for pattern '{pat}'"
                        ],
                    }
            return {'allowed': True, 'approval_required': False, 'reasons': []}

        if decision == 'review':
            return {
                'allowed': False,
                'approval_required': True,
                'reasons': [reason or f"Review required by rule for '{pat}'"],
            }

    # No rule matched -> default to review (safer default)
    return {
        'allowed': False,
        'approval_required': True,
        'reasons': ["No matching rule; default to review"],
    }