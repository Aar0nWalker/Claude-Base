#!/usr/bin/env bash
# Autopilot signal gathering: surface concrete improvement candidates from the code.
# Read-only, offline, fast. Prints TODO/FIXME/HACK markers so the autopilot loop can pick real
# work when the backlog runs dry. Production signals (error logs, analytics) are pulled by the
# loop itself — they outrank anything here.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)"
cd "$ROOT"

echo "# Candidates from the code ($(date -u +%Y-%m-%dT%H:%MZ))"
echo

# Stack-agnostic on purpose: scan tracked files, so vendor directories and build output are
# excluded by .gitignore rather than by a hardcoded list that goes stale on the next project.
hits="$(git ls-files -z 2>/dev/null \
  | xargs -0 grep -InE 'TODO|FIXME|HACK|XXX' 2>/dev/null \
  | grep -vE '(^|/)(CHANGELOG|README)\.md:' || true)"

if [[ -z "$hits" ]]; then
  echo "no TODO/FIXME/HACK markers found"
else
  echo "## TODO / FIXME / HACK / XXX"
  echo "$hits" | sed -E 's/^([^:]+:[0-9]+):[[:space:]]*/\1  /' | head -40
fi

echo
# `ponytail:` markers are deliberate, documented simplifications — a debt ledger, not a task list.
echo "# Deliberate shortcuts (ponytail:) are NOT tasks — revisit only when the ceiling they name is hit."
echo "# Next: production reliability and user-facing friction outrank every TODO above."
