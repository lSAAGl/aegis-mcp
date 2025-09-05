# Policy DSL v2 (Draft Spec)

The v2 policy is a **rules list** evaluated **top-down**. The first matching rule decides whether a tool call is **allowed**, **review (approval required)**, or **denied**. Optional caps can escalate an otherwise-allowed rule to **review** when an amount exceeds the cap.

## Goals
- Express per-tool decisions with glob patterns (e.g., `refunds.*`).
- Support three outcomes: `allow`, `review`, `deny`.
- Support amount caps (e.g., refunds ≤ $150 → allow; otherwise review).
- Preserve current behavior via a sensible default fallback rule.
- Keep config human-readable and git-friendly.

## Schema (informal)
```yaml
version: 2
rules:
  - match: <glob>                 # required; fnmatch-style, e.g. "refunds.*"
    decision: allow|review|deny   # required
    cap_cents: <int>              # optional; if present and amount_cents > cap, escalate allow→review
    ops: [<str>, ...]             # optional; only apply if request.op is in this set
    reason: <string>              # optional; human-friendly reason to include in responses
```

### Matching semantics
- **Tool match**: `fnmatch(tool, rule.match)`.
- **Op filter** (optional): if `ops` is present, the rule matches only when `op in rule.ops`.
- **Ordering**: rules are processed **in order**; **first match wins**.

### Decision semantics
- `allow`: permitted immediately. If `cap_cents` is **set** and an `amount_cents` is supplied that **exceeds** the cap, the outcome **escalates to `review`** (approval required). If `amount_cents` is missing, treat as within cap.
- `review`: always requires approval (creates/uses approval workflow).
- `deny`: hard block; never creates approval.

### Amount caps
- Only meaningful for monetary operations (e.g., refunds, payment links).
- If `cap_cents` is present **and** `amount_cents > cap_cents` → escalate `allow → review`. (If the rule is already `review`, remain `review`. If `deny`, remain `deny`.)

### Defaults & fallback
- Provide a final catch-all: `- match: "*"; decision: review` to mirror current behavior where unknown tools require approval.

## Examples
**Equivalent to current defaults** (refund cap 15000; payment link cap 25000; others require approval):
```yaml
version: 2
rules:
  - match: "refunds.*"
    decision: allow
    cap_cents: 15000
    ops: ["refund"]
    reason: "Refunds under cap are auto-approved"

  - match: "payment_links.create"
    decision: allow
    cap_cents: 25000
    reason: "Payment links under cap are auto-approved"

  - match: "*"
    decision: review
    reason: "Unlisted tools require approval"
```

**Denylist example** (block exports outright):
```yaml
version: 2
rules:
  - match: "users.export"
    decision: deny
    reason: "Data export is disabled"

  - match: "*"
    decision: review
```

## Backward compatibility
If a legacy `policy.yml` has:
```yaml
max_refund_cents: 15000
max_payment_link_cents: 25000
allow_tools:
  - "refunds.*"
  - "payment_links.create"
deny_tools: []
```
A migration produces:
```yaml
version: 2
rules:
  - match: "refunds.*"
    decision: allow
    cap_cents: 15000
    ops: ["refund"]
  - match: "payment_links.create"
    decision: allow
    cap_cents: 25000
  - match: "*"
    decision: review
```

## Validation & ergonomics (coming next)
- We will add Pydantic models + JSON Schema and a `/policy/validate` endpoint returning `{ ok, errors[] }`.
- Loader will accept both v1 (legacy) and v2, auto-converting v1 → v2 in-memory and surfacing a deprecation note via `/policy`.

## Notes
- Reasons are optional but recommended; they surface in `reasons[]` to explain decisions.
- Keep the rules list short and ordered by specificity (deny/allow first, catch-all last).