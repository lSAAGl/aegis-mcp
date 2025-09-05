VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
UVICORN=$(VENV)/bin/uvicorn
PYTEST=$(VENV)/bin/pytest

PY311=.venv311
PY311_BIN=$(PY311)/bin
PY311_PY=$(PY311_BIN)/python
PY311_PIP=$(PY311_BIN)/pip
PY311_PYTEST=$(PY311_BIN)/pytest

.PHONY: install run test mcp-install mcp-test mcp-run mcp-smoke approvals-demo approvals-open mcp-enforce policy-migrate policy-migrate-file docker-build docker-run docker-stop docker-test

# HTTP API (FastAPI) — uses .venv
install:
	$(PY) -m pip install --upgrade pip
	$(PIP) install -e .
	$(PIP) install fastapi uvicorn pyyaml pytest httpx

run:
	$(UVICORN) src.app.main:app --reload --host 127.0.0.1 --port 8000

test:
	PYTHONPATH=. $(PYTEST) -q

# MCP stdio server (FastMCP) — uses .venv311
mcp-install:
	$(PY311_PIP) install --upgrade pip
	$(PY311_PIP) install -e .
	$(PY311_PIP) install fastmcp fastapi uvicorn pyyaml pytest httpx

mcp-test:
	PYTHONPATH=. $(PY311_PYTEST) -q

mcp-run:
	$(PY311_PY) mcp_server.py

mcp-smoke:
	$(PY311_PY) smoke_client_direct.py

# --- Approvals demo helpers ---

# Creates a pending approval using the MCP env (.venv311)
approvals-demo:
	$(PY311_PY) -c "from mcp_server import require_approval; print(require_approval('ui-demo'))"

# Just prints the URL to open; use your OS open command or click it
approvals-open:
	@echo "Open: http://127.0.0.1:8000/ui/approvals"

# Enforcement smoke (direct import, no HTTP client required)
mcp-enforce:
	$(PY311_PY) smoke_enforce_direct.py

# Policy migration targets
policy-migrate:
	PYTHONPATH=. $(PY311_PY) tools/policy_migrate.py examples/policy_v2.yml | sed -n '1,80p'

policy-migrate-file:
	# Convert a v1 file in-place to v2 into stdout (redirect > new file if desired)
	@if [ -z "$(FILE)" ]; then echo 'usage: make policy-migrate-file FILE=path/to/policy.yml'; exit 2; fi; \
	PYTHONPATH=. $(PY311_PY) tools/policy_migrate.py $(FILE)

.PHONY: docker-build docker-run docker-stop docker-test
docker-build:
	docker build -t mcp-firewall:dev .

# Run HTTP API at :8000
docker-run:
	docker run --rm -p 8000:8000 \
	  -e POLICY_PATH=/data/policy.yml \
	  -v "$(PWD)":/data \
	  mcp-firewall:dev

# Run tests in a one-off container (optional: mounts repo and runs pytest)
# Note: For speed, CI runs pytest natively; this is a convenience for parity.
docker-test:
	docker run --rm -v "$(PWD)":/app -w /app mcp-firewall:dev pytest -q

# Stop all containers named mcp-firewall (best-effort)
docker-stop:
	-@docker ps -q --filter ancestor=mcp-firewall:dev | xargs -r docker stop