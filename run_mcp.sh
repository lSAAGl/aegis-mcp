#!/usr/bin/env bash
set -euo pipefail
# Optional: set a demo approval code (override as needed)
: "${APPROVAL_CODE:=123456}"
# Activate Python 3.11 venv and run the MCP stdio server
source .venv311/bin/activate
exec python mcp_server.py