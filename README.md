# AegisMCP — MCP Firewall

[![CI](https://github.com/lSAAGl/aegis-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/lSAAGl/aegis-mcp/actions/workflows/ci.yml)

**Open-source MCP Firewall**: Policy rules, audit logs, approvals workflow, and Web UI for AI/MCP tool-calling security.

AegisMCP provides a comprehensive guard and approval layer for MCP (Model Context Protocol) actions, featuring both HTTP API and MCP stdio server protocols, policy enforcement, approval workflows, audit logging, and production-ready packaging.

## 🚀 Features

### Core Components
- **🛡️ Policy Engine**: Rule-based allow/deny decisions with amount caps and pattern matching
- **📋 Audit Logging**: Complete trail of all tool calls and decisions in JSONL format  
- **✅ Approval Workflow**: Two-phase approval system with codes and Web UI
- **🌐 HTTP API**: 11 REST endpoints for policy, audit, guard, approvals, and enforcement
- **🔧 MCP Server**: FastMCP stdio server exposing 5 MCP tools for integration
- **📊 Web Interface**: HTML approval management interface
- **🐳 Docker Ready**: Multi-stage builds with optimized caching
- **⚡ CI/CD**: GitHub Actions with ruff, mypy, pytest, and coverage

### Policy System
- **v1 & v2 DSL**: Flexible policy configuration with migration support
- **Pattern Matching**: fnmatch-style tool name patterns (`refunds.*`, `users.export`)
- **Amount Caps**: Per-operation spending limits with escalation
- **Rule Evaluation**: Top-down, first-match-wins logic
- **Validation**: Schema validation with helpful error messages

## 🏃‍♂️ Quick Start

### HTTP API (Python 3.9+)
```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && pip install fastapi uvicorn pyyaml httpx

# Run server
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000

# Test endpoints
curl -s http://localhost:8000/health
curl -s http://localhost:8000/policy | jq .
curl -s -X POST http://localhost:8000/guard/check \
  -H 'content-type: application/json' \
  -d '{"tool":"refunds.refund","amount_cents":12000,"op":"refund"}' | jq .
```

### MCP Server (Python 3.11+)
```bash
# Setup Python 3.11 environment  
python3.11 -m venv .venv311 && source .venv311/bin/activate
pip install -e . && pip install fastmcp fastapi uvicorn pyyaml httpx

# Run MCP stdio server
./run_mcp.sh

# Test with direct client
python smoke_client_direct.py
```

### Docker
```bash
# Build and run
make docker-build
make docker-run

# Test
curl -s http://localhost:8000/health
```

## 📚 API Documentation

### HTTP Endpoints

#### Core Endpoints
- `GET /health` - Health check
- `GET /policy` - Current policy configuration  
- `POST /audit` - Write audit entry
- `POST /guard/check` - Policy evaluation for tool calls

#### Policy Management  
- `GET /policy/validate` - Validate policy configuration
- `POST /policy/migrate` - Migrate v1 to v2 policy format

#### Enforcement
- `POST /guard/enforce` - Unified enforcement (policy + audit + approval)

#### Approvals
- `GET /approvals` - List pending/completed approvals
- `POST /approvals/complete` - Complete approval with code
- `GET /ui/approvals` - Web interface for approval management

### MCP Tools
- `policy_get()` - Get current policy
- `audit_write(action, tool?, ok?, note?)` - Write audit entry
- `require_approval(dry_run_id, approval_code?)` - Two-phase approval
- `guard_check(tool, amount_cents?, op?)` - Policy evaluation  
- `firewall_enforce(tool, amount_cents?, op?, meta?)` - Unified enforcement

## 🛡️ Policy Configuration

### Basic Policy (v1)
```yaml
# policy.yml
max_refund_cents: 15000      # $150.00 cap
max_payment_link_cents: 25000  # $250.00 cap
allow_tools:
  - "refunds.*"
  - "payment_links.create"
deny_tools: []
```

### Advanced Policy (v2 DSL)
```yaml
# examples/policy_v2.yml
version: 2
rules:
  - match: "refunds.*"
    decision: allow
    cap_cents: 15000
    ops: ["refund"]
    reason: "Auto-approved refunds under $150"
    
  - match: "payment_links.create"
    decision: allow
    cap_cents: 25000
    reason: "Auto-approved payment links under $250"
    
  - match: "users.export"
    decision: deny
    reason: "User export forbidden"
    
  - match: "*"
    decision: review
    reason: "Default: requires approval"
```

## 🔄 Approval Workflow

### Two-Phase Approval
```bash
# 1. Create pending approval
curl -X POST http://localhost:8000/guard/enforce \
  -H 'content-type: application/json' \
  -d '{"tool":"refunds.refund","amount_cents":20000,"op":"refund"}'

# Response includes approval_id for tracking

# 2. Complete via Web UI or API
curl -X POST http://localhost:8000/approvals/complete \
  -H 'content-type: application/json' \
  -d '{"dry_run_id":"APPROVAL_ID","approval_code":"123456"}'
```

### Web Interface
```bash
# Start server and create demo approval
make run
make approvals-demo

# Open approval interface  
open http://localhost:8000/ui/approvals
```

## 🧪 Development

### Testing
```bash
# Run all tests
pytest -q

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific test suites
pytest tests/test_guard_v2.py -v
pytest tests/test_enforcer.py -v
```

### Code Quality
```bash
# Linting
ruff check .
ruff format .

# Type checking
mypy src

# Policy validation
python tools/cli.py validate policy.yml
```

### Policy Migration
```bash
# Migrate v1 to v2 policy
python tools/cli.py migrate policy.yml > policy_v2.yml

# Validate v2 policy
python tools/cli.py validate policy_v2.yml
```

## 🏗️ Architecture

### Dual Environment Setup
- **HTTP API**: Python 3.9+ (`.venv`) - FastAPI, basic functionality
- **MCP Server**: Python 3.11+ (`.venv311`) - FastMCP, full MCP protocol

### Key Components
```
src/app/
├── main.py           # FastAPI HTTP server (11 endpoints)
├── enforcer.py       # Unified enforcement logic  
├── policy_v2.py      # v2 policy schema & validation
├── engine_v2.py      # v2 rules evaluation engine
├── approvals.py      # Approval workflow management
├── guard.py          # v1 policy evaluation (legacy)
├── policy.py         # Policy loading & v1/v2 handling
└── audit.py          # Audit logging utilities

mcp_server.py         # FastMCP stdio server (5 tools)
tools/cli.py         # CLI utilities (validate/migrate)
```

### Data Flow
1. **Tool Request** → Policy Engine → Allow/Review/Deny
2. **If Review** → Create Approval → Web UI → Complete/Deny  
3. **All Actions** → Audit Log → Compliance Trail

## 📊 Monitoring & Compliance

### Audit Trail
```bash
# View recent activity
tail -f audit.log

# Search for specific actions
grep "refund" audit.log | jq .

# Filter by status
jq 'select(.ok == false)' audit.log
```

### Approval Tracking
```bash
# View pending approvals
tail -f approvals.log | jq 'select(.status == "pending")'

# Approval completion rates
jq -r '.status' approvals.log | sort | uniq -c
```

## 🐳 Production Deployment

### Docker
```dockerfile
FROM python:3.11-slim
# Optimized multi-stage build with layer caching
# Default: HTTP API on port 8000
# Override: CMD to run MCP stdio server
```

### Environment Variables
```bash
# Policy & data paths
POLICY_PATH=/app/config/policy.yml
AUDIT_PATH=/app/logs/audit.log  
APPROVALS_PATH=/app/logs/approvals.log

# Security
APPROVAL_CODE=your-secure-code-here

# Monitoring
LOG_LEVEL=INFO
```

## 🔧 CLI Tools

### Policy Management
```bash
# Validate policy syntax
./tools/cli.py validate policy.yml

# Migrate v1 → v2
./tools/cli.py migrate policy.yml > policy_v2.yml

# Validate migrated policy  
./tools/cli.py validate policy_v2.yml
```

### Migration Helper
```bash
# Automated migration with backup
python tools/policy_migrate.py policy.yml --backup
```

## 🚀 CI/CD

### GitHub Actions Workflow
- **Python 3.11** with pip caching
- **Linting**: ruff with auto-fix
- **Type Checking**: mypy with strict mode
- **Testing**: pytest with coverage reporting
- **Dependency Updates**: Dependabot (weekly)

### Quality Gates
```yaml
# .github/workflows/ci.yml
- Ruff linting (E, F, I rules)
- MyPy type checking (strict)  
- Pytest (all tests must pass)
- Coverage reporting (terminal)
```

## 📈 Roadmap

### Completed ✅
- [x] HTTP API with 11 endpoints
- [x] MCP stdio server with 5 tools  
- [x] Policy engine (v1 & v2 DSL)
- [x] Approval workflow with Web UI
- [x] Unified enforcement layer
- [x] Audit logging & compliance
- [x] Docker packaging & CI/CD
- [x] Migration tools & validation

### Future Enhancements 🔄
- [ ] Web dashboard for policy management
- [ ] Webhook notifications for approvals  
- [ ] RBAC (Role-Based Access Control)
- [ ] Metrics & analytics dashboard
- [ ] Integration with external approval systems
- [ ] Advanced rule conditions (time, user context)

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)  
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup
```bash
# Clone and setup
git clone https://github.com/lSAAGl/aegis-mcp.git
cd aegis-mcp

# HTTP environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e . && pip install -r requirements-dev.txt

# MCP environment  
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -e . && pip install fastmcp

# Run tests
pytest -q
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **FastMCP** - MCP server implementation
- **Pydantic** - Data validation and settings
- **Ruff** - Fast Python linter
- **pytest** - Testing framework

---

**AegisMCP** - Secure your AI tool calls with confidence! 🛡️✨