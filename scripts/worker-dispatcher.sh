#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

AGENT="${1:-Codex}"
INTERVAL="${WORKER_DISPATCH_INTERVAL_SECONDS:-5}"
DISPATCH_TIMEOUT="${WORKER_CODEX_DISPATCH_TIMEOUT_SECONDS:-120}"
REQUIRE_HEADROOM="${WORKER_CODEX_REQUIRE_HEADROOM:-1}"

headroom_required() {
  [[ "$AGENT" == "Codex" && "$REQUIRE_HEADROOM" != "0" && "${REQUIRE_HEADROOM,,}" != "false" ]]
}

ensure_headroom() {
  headroom_required || return 0
  ./scripts/start-headroom.sh >/dev/null 2>&1 || return 1
  curl --noproxy "*" -fsS -m 2 http://127.0.0.1:8788/livez >/dev/null 2>&1
}

echo "Worker dispatcher started $AGENT"

while true; do
  task="$(./scripts/worker-bot.sh next "$AGENT" 2>&1)"
  rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "worker-bot next failed rc=$rc: $task" >&2
    sleep "$INTERVAL"
    continue
  fi

  if [[ -z "$task" || "$task" == "NO_TASK" ]]; then
    sleep "$INTERVAL"
    continue
  fi

  task_id="$(sed -n 's/^#\([0-9]\+\).*/\1/p' <<<"$task" | head -n 1)"
  if [[ -z "$task_id" ]]; then
    echo "Cannot parse task id from: $task" >&2
    sleep "$INTERVAL"
    continue
  fi

  bot_context="$(./scripts/worker-bot.sh context "$AGENT" 2>/dev/null || true)"

  prompt="$(
cat <<EOF
Telegram worker-bot task $AGENT:

$task

Treat it as if the user wrote it in the current project chat. Use current repo and chat context when available.
$(if [[ -n "$bot_context" ]]; then printf '\n<worker_bot_context>\n%s\n</worker_bot_context>\n' "$bot_context"; fi)
Work on the task now. When it is genuinely complete, run:
./scripts/worker-bot.sh done $task_id
EOF
)"

  ./scripts/worker-bot.sh status "$AGENT" "Взял задачу из Telegram: $task" >/dev/null 2>&1 || true
  echo "Dispatching task #$task_id to Codex app-server"
  dispatch_log=".agents/worker-bot/dispatch-$task_id.log"
  if ! ensure_headroom; then
    echo "Headroom is required for Codex worker-bot dispatch, but 127.0.0.1:8788 is not healthy" >"$dispatch_log"
    ./scripts/worker-bot.sh release "$task_id" "Headroom недоступен, задача не отправлена в Codex" >/dev/null 2>&1 || true
    sleep "$INTERVAL"
    continue
  fi
  python3 scripts/codex-app-send.py --timeout "$DISPATCH_TIMEOUT" "$prompt" >"$dispatch_log" 2>&1 || {
    echo "Codex app-server dispatch failed for task #$task_id. See $dispatch_log" >&2
    ./scripts/worker-bot.sh status "$AGENT" "Не смог отправить задачу в Codex app-server: $task" >/dev/null 2>&1 || true
    ./scripts/worker-bot.sh release "$task_id" "ошибка отправки в Codex app-server" >/dev/null 2>&1 || true
  }
done
