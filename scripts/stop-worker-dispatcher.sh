#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PID_FILE=".agents/worker-bot/dispatcher.pid"
if [[ ! -f "$PID_FILE" ]]; then
  echo "Worker dispatcher is not running."
  exit 0
fi

pid="$(cat "$PID_FILE" || true)"
if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
  kill "$pid"
  echo "Worker dispatcher stopped: $pid"
else
  echo "Worker dispatcher process not found."
fi
rm -f "$PID_FILE"
