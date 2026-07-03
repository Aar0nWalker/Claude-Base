#!/usr/bin/env bash
# Rollback — remote wrapper around `start.sh --rollback`. Does NOT upload files
# and does NOT rebuild: switches api/worker/web back to the :rollback images
# saved by the previous successful deploy. db/redis/storage are untouched.
#
# Usage: ./rollback.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then echo "[ERROR] .env not found in $ROOT" >&2; exit 1; fi
DEPLOY_PATH="$(grep -E '^DEPLOY_PATH=' .env | head -1 | cut -d= -f2- | tr -d '\r')"
DEPLOY_SSH="$(grep -E '^DEPLOY_SSH=' .env | head -1 | cut -d= -f2- | tr -d '\r')"
if [[ -z "${DEPLOY_SSH:-}" ]]; then
  DEPLOY_SSH="$(grep -E '^DEPLOY_WINSCP_SITE=' .env | head -1 | cut -d= -f2- | tr -d '\r')"
fi
if [[ -z "${DEPLOY_PATH:-}" || -z "${DEPLOY_SSH:-}" ]]; then
  echo "[ERROR] DEPLOY_PATH and DEPLOY_SSH must be set in .env" >&2; exit 1
fi

rm -f "$ROOT/rollback.log" 2>/dev/null || true
echo "[1/1] Rolling back api/worker/web on server..."
echo "      -> $DEPLOY_SSH:$DEPLOY_PATH"
ssh "$DEPLOY_SSH" "cd '$DEPLOY_PATH' && bash start.sh --rollback" 2>&1 | tee "$ROOT/rollback.log"
echo; echo "[OK] Rollback finished."; echo "     Site: https://{{DOMAIN}}"
