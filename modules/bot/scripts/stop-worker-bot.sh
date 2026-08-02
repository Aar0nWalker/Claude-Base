#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
PID_FILE=".agents/worker-bot/bot.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Worker bot is not running (no pid file)."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID" 2>/dev/null || true
  echo "Worker bot stopped (pid $PID)."
else
  echo "Worker bot was not running (stale pid $PID)."
fi
rm -f "$PID_FILE"
