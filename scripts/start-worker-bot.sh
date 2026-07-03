#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DOCKER=(docker)
if ! command -v docker >/dev/null 2>&1; then
  DOCKER=(docker.exe)
fi

mkdir -p .agents/worker-bot
"${DOCKER[@]}" compose --profile worker-bot up -d worker-bot
./scripts/start-worker-dispatcher.sh
echo "Worker bot started in Docker."
echo "Logs: docker compose --profile worker-bot logs -f worker-bot"
