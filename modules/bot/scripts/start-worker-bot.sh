#!/usr/bin/env bash
# Start the bot's polling loop in the background and record its pid.
# Idempotent: a second run does nothing if the bot is already alive.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
mkdir -p .agents/worker-bot
PID_FILE=".agents/worker-bot/bot.pid"
LOG_FILE=".agents/worker-bot/bot.log"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Worker bot already running (pid $(cat "$PID_FILE"))."
  exit 0
fi

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

# setsid so the loop survives this shell closing.
setsid "$PY" modules/bot/scripts/worker_bot.py run >>"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "Worker bot started (pid $(cat "$PID_FILE"))."
echo "Logs: tail -f $LOG_FILE"
