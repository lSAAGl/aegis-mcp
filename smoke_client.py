import asyncio
import json
import os
from typing import Any

from mcp.client.session import StdioServerParameters, connect_stdio

# Helper to convert various SDK objects to plain JSON

def _to_json(obj: Any) -> Any:
    try:
        if hasattr(obj, "model_dump_json"):
            return json.loads(obj.model_dump_json())
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
    except Exception:
        pass
    if isinstance(obj, (dict, list, str, int, float, type(None), bool)):
        return obj
    return str(obj)


def _flatten_content(resp: Any) -> Any:
    # Works with MCP SDK ToolResult structures and FastMCP JSON outputs
    try:
        items = []
        for c in getattr(resp, "content", []) or []:
            t = getattr(c, "type", None)
            if t == "text" and hasattr(c, "text"):
                items.append(c.text)
            elif t == "json" and hasattr(c, "value"):
                items.append(c.value)
            else:
                items.append(_to_json(c))
        if items:
            return items[0] if len(items) == 1 else items
    except Exception:
        pass
    return _to_json(resp)


async def main():
    # Spawn the local MCP stdio server via our run script
    cmd = "/bin/bash"
    args = ["-lc", f"cd '{os.getcwd()}' && ./run_mcp.sh"]
    params = StdioServerParameters(command=cmd, args=args)

    async with connect_stdio(params) as session:
        await session.initialize()
        tools = await session.list_tools()
        tool_names = [getattr(t, "name", str(t)) for t in tools]
        print("TOOLS", json.dumps(tool_names))

        # 1) policy_get
        r = await session.call_tool("policy_get", {})
        print("POLICY_GET", json.dumps(_flatten_content(r)))

        # 2) audit_write
        r = await session.call_tool(
            "audit_write",
            {"action": "smoke", "tool": "client", "ok": True, "note": "wf-50"},
        )
        print("AUDIT_WRITE", json.dumps(_flatten_content(r)))

        # 3) require_approval (two-phase)
        r1 = await session.call_tool("require_approval", {"dry_run_id": "dry-smoke"})
        print("APPROVAL_1", json.dumps(_flatten_content(r1)))

        code = os.environ.get("APPROVAL_CODE", "123456")
        r2 = await session.call_tool(
            "require_approval", {"dry_run_id": "dry-smoke", "approval_code": code}
        )
        print("APPROVAL_2", json.dumps(_flatten_content(r2)))


if __name__ == "__main__":
    asyncio.run(main())