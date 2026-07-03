#!/usr/bin/env bash
# Deploy — upload the project over SSH with rsync (byte-exact, LF preserved),
# then run `start.sh --rebuild` on the server (rolling rebuild: build new images
# while the old site stays up, then recreate api/worker/web).
#
# Prereqs: rsync + ssh, SSH access to the server. Set in .env:
#   DEPLOY_PATH=/opt/{{PROJECT_SLUG}}
#   DEPLOY_SSH=root@your.server.ip     (or an ~/.ssh/config Host alias)
#
# Usage: ./deploy.sh          (DRY_RUN=1 ./deploy.sh to preview without changes)
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
RELEASE_SHA="$(git rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"
RELEASE_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

rm -f "$ROOT/deploy.log" 2>/dev/null || true
echo "[1/2] Uploading files + rolling rebuild (api/worker/web)..."
echo "      → $DEPLOY_SSH:$DEPLOY_PATH   version: $RELEASE_BRANCH@$RELEASE_SHA"

ssh "$DEPLOY_SSH" "mkdir -p '$DEPLOY_PATH' '$DEPLOY_PATH/backups' '$DEPLOY_PATH/frontend' '$DEPLOY_PATH/backend'"

DRY=""; RSYNC_REPORT=""
if [[ -n "${DRY_RUN:-}" ]]; then
  DRY="--dry-run"; RSYNC_REPORT="--itemize-changes"
  echo "   *** DRY RUN — nothing uploaded/deleted, rebuild skipped ***"
fi

# Optional local backend test gate before shipping (skip with SKIP_LOCAL_DOCKER_TESTS=1).
if [[ -z "${DRY_RUN:-}" && -z "${SKIP_LOCAL_DOCKER_TESTS:-}" && -f backend/Dockerfile.test ]]; then
  echo "[TEST] Backend pytest in Docker..."
  docker build -f backend/Dockerfile.test -t {{PROJECT_SLUG}}-backend-tests:local backend
  docker run --rm {{PROJECT_SLUG}}-backend-tests:local
fi

RSYNC_MIRROR="rsync -az $DRY $RSYNC_REPORT --delete --no-perms --no-owner --no-group"
RSYNC_PUT="rsync -az $DRY $RSYNC_REPORT --no-perms --no-owner --no-group"

# Tests + build artifacts stay local.
$RSYNC_MIRROR \
  --exclude 'node_modules/' --exclude '.next/' --exclude '*.tsbuildinfo' \
  --exclude 'e2e/' --exclude 'playwright.config.ts' \
  frontend/ "$DEPLOY_SSH:$DEPLOY_PATH/frontend/"

$RSYNC_MIRROR \
  --exclude '__pycache__/' --exclude '*.pyc' --exclude '.venv/' --exclude '.env' \
  --exclude 'tests/' --exclude 'pytest.ini' --exclude 'requirements-dev.txt' \
  backend/ "$DEPLOY_SSH:$DEPLOY_PATH/backend/"

# Root files (upload only, no --delete so server-side frontend/backend/backups stay safe).
$RSYNC_PUT .env docker-compose.yml install.sh start.sh deploy.sh rollback.sh "$DEPLOY_SSH:$DEPLOY_PATH/"
# Scripts (worker-bot, killswitch) — optional, ship if present.
[[ -d scripts ]] && $RSYNC_MIRROR --exclude '__pycache__/' scripts/ "$DEPLOY_SSH:$DEPLOY_PATH/scripts/"

if [[ -n "${DRY_RUN:-}" ]]; then
  echo; echo "[DRY RUN] No changes made. Re-run without DRY_RUN to deploy."; exit 0
fi

echo "[2/2] Rebuilding on the server (start.sh --rebuild)..."
ssh "$DEPLOY_SSH" "cd '$DEPLOY_PATH' && bash start.sh --rebuild" 2>&1 | tee "$ROOT/deploy.log"

echo; echo "[OK] Deploy complete."; echo "     Site: https://{{DOMAIN}}"
