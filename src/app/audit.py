import json
import os
import time
import uuid
from typing import Dict


def _audit_path() -> str:
    return os.environ.get("AUDIT_PATH", "audit.log")


def write(event: Dict) -> Dict:
    """Append an audit event as a JSONL record.
    Uses AUDIT_PATH env at *call time* for test isolation.
    """
    trace_id = str(uuid.uuid4())
    rec = dict(event)
    rec["ts"] = int(time.time())
    rec["trace_id"] = trace_id
    path = _audit_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return {"trace_id": trace_id, "path": path}