#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p .agents/worker-bot
PID_FILE=".agents/worker-bot/dispatcher.pid"
LOG_FILE=".agents/worker-bot/dispatcher.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" >/dev/null 2>&1; then
    echo "Worker dispatcher already running: $old_pid"
    exit 0
  fi
fi

setsid bash -c 'exec bash "$1/scripts/worker-dispatcher.sh" Codex >"$2" 2>&1' _ "$ROOT" "$LOG_FILE" </dev/null &
echo "$!" >"$PID_FILE"
echo "Worker dispatcher started: $(cat "$PID_FILE")"
echo "Logs: $LOG_FILE"
