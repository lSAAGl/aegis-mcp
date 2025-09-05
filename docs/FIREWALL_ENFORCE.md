# Firewall Enforce

The `firewall_enforce` function is the unified entry-point for MCP Firewall decisions. It combines policy evaluation, audit logging, and approval creation into a single call.

## Function Signature

```python
def firewall_enforce(
    tool: str, 
    amount_cents: Optional[int] = None, 
    op: Optional[str] = None, 
    meta: Optional[dict] = None
) -> dict
```

## Return Format

```python
{
    "allowed": bool,              # True if action can proceed immediately
    "approval_required": bool,    # True if pending approval needed
    "status": str,               # "allowed" | "pending" | "blocked"  
    "reasons": List[str],        # Policy evaluation reasons
    "approval_id": str           # Only present if approval_required=True
}
```

## Usage via HTTP API

### POST /guard/enforce

```bash
curl -X POST http://127.0.0.1:8000/guard/enforce \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "refunds.refund",
    "amount_cents": 12000,
    "op": "refund"
  }'
```

## Usage via MCP

The `firewall_enforce` tool is available as an MCP tool when running the stdio server:

```python
# Call via MCP client
result = mcp_client.call_tool("firewall_enforce", {
    "tool": "users.export"
})
```

## Three Enforcement Outcomes

### 1. Allowed (status="allowed")
- Policy allows the action immediately
- No approval required
- Action can proceed

### 2. Pending (status="pending") 
- Policy requires approval for this action
- Creates pending approval record in approvals.log
- Returns approval_id for tracking

### 3. Blocked (status="blocked")
- Policy explicitly denies this action
- No approval possible
- Action must not proceed

## Quick Demo

Run the direct enforcement demo:

```bash
make mcp-enforce
```

This demonstrates all three outcomes using the default policy configuration.