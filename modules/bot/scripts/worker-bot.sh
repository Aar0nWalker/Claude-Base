#!/usr/bin/env bash
# CLI entry point for the worker bot. `worker_bot.py` is pure stdlib, so this just runs it —
# no container, no virtualenv, no dependency install.
#
#   ./modules/bot/scripts/worker-bot.sh queue
#   ./modules/bot/scripts/worker-bot.sh next Claude
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
mkdir -p .agents/worker-bot

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

exec "$PY" modules/bot/scripts/worker_bot.py "$@"
