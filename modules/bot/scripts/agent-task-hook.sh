#!/usr/bin/env bash
set -euo pipefail

AGENT="${1:-Claude}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

# Silent no-op if the bot module was removed — a hook must never break a session.
[[ -f modules/bot/scripts/worker-bot.sh ]] || exit 0

task_context="$(bash modules/bot/scripts/worker-bot.sh hook "$AGENT" 2>/dev/null || true)"
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
        "hookEventName": os.environ.get("AGENT_HOOK_EVENT", "SessionStart"),
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
