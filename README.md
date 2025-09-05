# MCP Firewall MVP

A small FastAPI app that will become the guard/approval layer for MCP actions. Today it ships:

- **HTTP API** (FastAPI):
  - `GET /health` → `{ "status": "ok" }`
  - `GET /policy` → returns the active policy (from `policy.yml` or defaults)
  - `POST /audit` → appends a JSON line to `audit.log` and returns a `trace_id`
  - `POST /guard/check` → policy decision for a prospective tool call (see examples)
- **MCP stdio server** (FastMCP): exposes guard tools
  - `policy_get()` → current policy dict
  - `audit_write(action, tool?, ok?, note?)` → writes to `audit.log`
  - `require_approval(dry_run_id, approval_code?)` → two-phase approval
  - `guard_check(tool, amount_cents?, op?)` → same policy decision as HTTP endpoint

## Quick start: HTTP API (FastAPI)

```bash
# Create and activate a virtual environment (Python 3.9+ is fine for HTTP API)
python3 -m venv .venv
source .venv/bin/activate

# Install
python -m pip install --upgrade pip
pip install -e .
pip install fastapi uvicorn pyyaml pytest httpx

# Run the server
uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000
```

Test it:
```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/policy | jq .

# Write an audit entry (creates/updates audit.log)
curl -s -X POST http://127.0.0.1:8000/audit \
  -H 'content-type: application/json' \
  -d '{"action":"demo","tool":"curl","ok":true,"note":"readme"}'

tail -n 3 audit.log
```

### Guard check via HTTP
The policy rules engine evaluates allow/deny and amount caps from `policy.yml`.

```bash
# Allowed: refund under cap (default cap 15000)
curl -s -X POST http://127.0.0.1:8000/guard/check \
  -H 'content-type: application/json' \
  -d '{"tool":"refunds.refund","amount_cents":12000,"op":"refund"}' | jq .

# Requires approval: refund over cap
curl -s -X POST http://127.0.0.1:8000/guard/check \
  -H 'content-type: application/json' \
  -d '{"tool":"refunds.refund","amount_cents":20000,"op":"refund"}' | jq .

# Requires approval: tool not in allow list
curl -s -X POST http://127.0.0.1:8000/guard/check \
  -H 'content-type: application/json' \
  -d '{"tool":"users.export"}' | jq .
```

## MCP stdio server (FastMCP)

> Requires **Python 3.11+**. This repo uses a separate env `.venv311` for MCP while keeping the HTTP API in `.venv`.

```bash
# Create and activate Python 3.11 env
python3.11 -m venv .venv311
source .venv311/bin/activate

# Install deps (includes FastMCP)
pip install --upgrade pip
pip install -e .
pip install fastmcp fastapi uvicorn pyyaml pytest httpx

# Start the MCP stdio server
./run_mcp.sh
```
You should see a FastMCP banner showing:
- Server name: `mcp-firewall`
- Transport: `STDIO`

### Programmatic smoke test (no MCP SDK client needed)
```bash
# With .venv311 active
python smoke_client_direct.py

tail -n 5 audit.log
tail -n 5 approvals.log
```
Expected:
- `TOOLS ["policy_get","audit_write","require_approval","guard_check"]`
- `POLICY_GET` shows keys: `max_refund_cents`, `max_payment_link_cents`, `allow_tools`, `deny_tools`.
- `AUDIT_WRITE` returns `{ok:true, trace_id:"...", path:"audit.log"}` and `audit.log` grows by one line.
- `APPROVAL_1` → `status: "pending"`, then `APPROVAL_2` → `status: "approved"`.
- `GUARD_refund_under` → allowed; `GUARD_refund_over` → approval_required with a cap reason; `GUARD_users_export` → approval_required with allow-list reason.

### Use with Cursor (optional)
1) **Settings → MCP Servers → Add Local Server**  
2) **Name:** `mcp-firewall`  
3) **Command:** `/bin/bash`  
4) **Args:** `-lc`, `cd '<project_path>' && ./run_mcp.sh`  
5) **Working Dir:** your project root  
Then run tools in MCP Inspector:
- `policy_get`
- `audit_write` with `{action:"cursor", tool:"inspector", ok:true, note:"readme"}`
- `require_approval` twice (first pending, then with `approval_code:"123456"`)
- `guard_check` with a few scenarios (see HTTP examples above)

### Approvals Web UI

Start the HTTP server, create a pending approval, and open the page:

```bash
# HTTP API
make run

# In another terminal (Python 3.11 env already set up via `make mcp-install`)
make approvals-demo

# Visit the UI:
make approvals-open
# -> http://127.0.0.1:8000/ui/approvals
```

From the page, paste the approval code (default `123456`) and click **Complete**.
You can also complete via HTTP:

```bash
curl -s -X POST http://127.0.0.1:8000/approvals/complete \
  -H 'content-type: application/json' \
  -d '{"dry_run_id":"ui-demo","approval_code":"123456"}' | jq .
```

### Docker (quick start)

```bash
# Build the image
make docker-build

# Run the HTTP API on http://127.0.0.1:8000 (mount your policy.yml if desired)
make docker-run

# Try it
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/policy | jq .

# Stop container
make docker-stop
```

CI runs ruff + mypy + pytest on pushes/PRs. See `.github/workflows/ci.yml`.

## Tests

```bash
# HTTP + MCP unit tests (either env works, prefer .venv311)
pytest -q
# If imports fail, try:
PYTHONPATH=. pytest -q
```

## Policy file

Edit `policy.yml`:
```yaml
max_refund_cents: 15000
max_payment_link_cents: 25000
allow_tools:
  - "refunds.*"
  - "payment_links.create"
deny_tools: []
```
Optional env vars:
- `POLICY_PATH` → path to policy file (default `policy.yml`)
- `AUDIT_PATH` → path to audit log (default `audit.log`)
- `APPROVAL_CODE` → override approval code for `require_approval` (default `123456`)

## Troubleshooting
- **Port already in use (HTTP API)**: run on another port
  ```bash
  uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8001
  ```
- **ImportError for `src.app.main` in tests**: ensure venv is active and run `pip install -e .`, or run tests with `PYTHONPATH=.`.
- **`policy.yml` not found**: app falls back to safe defaults; set `POLICY_PATH` if your file lives elsewhere.
- **No audit entries**: confirm POST body is JSON; check `AUDIT_PATH`.

## Project layout
```
mcp-firewall/
├─ src/app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ policy.py
│  ├─ audit.py
│  └─ guard.py
├─ mcp_server.py
├─ run_mcp.sh
├─ smoke_client_direct.py
├─ tests/
│  ├─ test_smoke.py
│  ├─ test_health.py
│  ├─ test_mcp_tools.py
│  └─ test_guard.py
├─ policy.yml
├─ audit.log           # created after first POST /audit or audit_write()
├─ approvals.log       # created by require_approval()
├─ pyproject.toml
├─ Makefile            # HTTP & MCP helpers (.venv / .venv311)
└─ README.md
```