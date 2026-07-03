#!/usr/bin/env bash
# keepalive — idempotent recovery so overnight work resumes itself after a temporary
# net drop or a helper dying. Safe to run repeatedly (Task Scheduler / cron / autopilot
# step 0). Brings any stopped bot service back up and respawns the host dispatcher.
#
# Why it's needed: Docker services already carry `restart: unless-stopped` and the bot's
# poll loop retries every 5s on any error, so the container side self-heals. The gaps this
# covers: the host worker-dispatcher has no restart policy, and a service that was `stop`ped
# (or lost on a Docker restart) needs a nudge to come back.
#
# Usage:  bash scripts/keepalive.sh
# Suggested: run every ~5 min via Windows Task Scheduler (survives reboots), or let the
# autopilot loop call it at the start of each cycle.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p .agents/worker-bot
LOG=".agents/worker-bot/keepalive.log"
ts() { date -u +%FT%TZ; }

DOCKER=(docker); command -v docker >/dev/null 2>&1 || DOCKER=(docker.exe)

# 1) Bot container: `up -d` is a no-op if healthy, revives it if stopped/lost.
if "${DOCKER[@]}" compose --profile worker-bot up -d worker-bot >>"$LOG" 2>&1; then
  :
else
  echo "$(ts) compose up worker-bot failed" >>"$LOG"
fi

# 2) Host dispatcher has no restart policy — this no-ops if alive, respawns if its pid died.
./scripts/start-worker-dispatcher.sh >>"$LOG" 2>&1 || echo "$(ts) dispatcher start failed" >>"$LOG"

# 3) Connectivity heartbeat — records whether egress is back, without failing the script.
if curl -sS -o /dev/null --max-time 8 https://api.telegram.org 2>/dev/null; then
  echo "$(ts) ok: bot + dispatcher up, net reachable" >>"$LOG"
else
  echo "$(ts) net unreachable — services up, will recover when the link returns" >>"$LOG"
fi
