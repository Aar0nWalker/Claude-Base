#!/usr/bin/env bash
# keepalive — idempotent recovery so unattended work resumes itself after a temporary net drop
# or the bot loop dying. Safe to run repeatedly (Task Scheduler / cron / autopilot step 0).
#
# Why it's needed: the bot's poll loop retries every few seconds on any error, so it survives a
# flaky network on its own. The gap this covers is the process being gone entirely — killed,
# lost on reboot, or stopped by hand.
#
# Usage:  bash modules/bot/scripts/keepalive.sh
# Suggested: every ~5 min via Task Scheduler / cron, or at the start of each autopilot cycle.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
mkdir -p .agents/worker-bot
LOG=".agents/worker-bot/keepalive.log"
ts() { date -u +%FT%TZ; }

# 1) Bot loop: the start script is idempotent — no-op if alive, respawn if the pid is gone.
if bash modules/bot/scripts/start-worker-bot.sh >>"$LOG" 2>&1; then
  :
else
  echo "$(ts) starting worker bot failed" >>"$LOG"
fi

# 2) Connectivity heartbeat — records whether egress is back, without failing the script.
if curl -sS -o /dev/null --max-time 8 https://api.telegram.org 2>/dev/null; then
  echo "$(ts) ok: bot up, net reachable" >>"$LOG"
else
  echo "$(ts) net unreachable — bot up, will recover when the link returns" >>"$LOG"
fi
