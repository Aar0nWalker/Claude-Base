#!/usr/bin/env bash
set -euo pipefail

AGENT="${1:-Codex}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

task_context="$(./scripts/worker-bot.sh hook "$AGENT" 2>/dev/null || true)"
if [[ -z "$task_context" ]]; then
  exit 0
fi

if [[ -n "${PLUGIN_DATA:-}" ]]; then
  TASK_CONTEXT="$task_context" python3 - <<'PY'
import json
import os

print(json.dumps({
    "systemMessage": "TELEGRAM_WORKER_TASK",
    "hookSpecificOutput": {
        "hookEventName": os.environ.get("CODEX_HOOK_EVENT", "SessionStart"),
        "additionalContext": f"<telegram_worker_task>\n{os.environ['TASK_CONTEXT']}\n</telegram_worker_task>",
    },
}, ensure_ascii=False))
PY
  exit 0
fi

cat <<EOF

<telegram_worker_task>
$task_context
</telegram_worker_task>

EOF
