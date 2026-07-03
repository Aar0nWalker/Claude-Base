#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DOCKER=(docker)
if ! command -v docker >/dev/null 2>&1; then
  DOCKER=(docker.exe)
fi

./scripts/stop-worker-dispatcher.sh
"${DOCKER[@]}" compose --profile worker-bot stop worker-bot
echo "Worker bot stopped."
