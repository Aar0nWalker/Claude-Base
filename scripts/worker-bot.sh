#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p .agents/worker-bot

DOCKER=(docker)
if ! command -v docker >/dev/null 2>&1; then
  DOCKER=(docker.exe)
fi

container_id=""
if command -v "${DOCKER[0]}" >/dev/null 2>&1; then
  container_id="$("${DOCKER[@]}" compose --profile worker-bot ps --status running -q worker-bot 2>/dev/null || true)"
fi

if [[ -n "$container_id" ]]; then
  "${DOCKER[@]}" compose --profile worker-bot exec -T worker-bot python3 scripts/worker_bot.py "$@" && exit 0
fi

if command -v "${DOCKER[0]}" >/dev/null 2>&1 && "${DOCKER[@]}" info >/dev/null 2>&1; then
  "${DOCKER[@]}" compose --profile worker-bot run --rm --no-TTY worker-bot python3 scripts/worker_bot.py "$@"
else
  python3 scripts/worker_bot.py "$@"
fi
