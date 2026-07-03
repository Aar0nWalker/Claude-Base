import json
import os
from pathlib import Path


_DEFAULT_RELEASE = {
    "git_sha": os.getenv("RELEASE_SHA", "unknown"),
    "branch": os.getenv("RELEASE_BRANCH", "unknown"),
    "built_at": os.getenv("RELEASE_BUILT_AT", "unknown"),
    "deployed_at": os.getenv("RELEASE_DEPLOYED_AT", "unknown"),
    "rollback_from": os.getenv("RELEASE_ROLLBACK_FROM", ""),
}


def release_info() -> dict[str, str]:
    path = Path(__file__).with_name("release_info.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    out = dict(_DEFAULT_RELEASE)
    if isinstance(data, dict):
        out.update({str(k): str(v) for k, v in data.items() if v is not None})
    return out
