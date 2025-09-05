import os, json
from typing import List, Dict, Optional


def _approvals_path() -> str:
    return os.environ.get("APPROVALS_PATH", "approvals.log")


def read_approvals(path: Optional[str] = None) -> List[Dict]:
    p = path or _approvals_path()
    records: List[Dict] = []
    if not os.path.exists(p):
        return records
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                records.append(obj)
            except Exception:
                # Skip malformed lines
                pass
    return records


def _summarize_by_dry_run_id(records: List[Dict]) -> List[Dict]:
    by_id: Dict[str, Dict] = {}
    for r in records:
        did = r.get("dry_run_id")
        if not did:
            continue
        by_id[did] = r  # keep LAST occurrence (latest status)
    out = list(by_id.values())
    out.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return out


def list_approvals(path: Optional[str] = None) -> List[Dict]:
    return _summarize_by_dry_run_id(read_approvals(path))


def list_pending(path: Optional[str] = None) -> List[Dict]:
    return [r for r in list_approvals(path) if r.get("status") == "pending"]


def complete_approval(dry_run_id: str, code: str) -> Dict:
    """Complete an approval by delegating to mcp_server.require_approval.
    Returns a dict with keys including ok, status, approval_id (and possibly trace info).
    """
    from mcp_server import require_approval  # local import to avoid cycles
    return require_approval(dry_run_id, approval_code=code)