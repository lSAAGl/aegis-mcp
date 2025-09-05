FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
# Copy project metadata first (better layer caching)
COPY pyproject.toml ./
# Install runtime deps and the package
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir fastapi uvicorn pyyaml fastmcp httpx anyio \
    && pip install --no-cache-dir -e .
# Copy source and scripts
COPY src ./src
COPY mcp_server.py run_mcp.sh ./
# Expose HTTP API port (MCP uses stdio when run via run_mcp.sh)
EXPOSE 8000
# Default command runs the HTTP API; override with CMD to run MCP if desired
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]