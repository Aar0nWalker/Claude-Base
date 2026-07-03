#!/usr/bin/env bash
# Autopilot signal gathering: surface concrete improvement candidates from the code.
# Read-only. Prints grouped TODO/FIXME/HACK/ponytail markers so the autopilot loop
# can pick real work when the backlog runs dry. Prod/analytics signals are pulled
# separately by the loop (redis job errors, admin funnel) — kept out of here to stay
# offline-safe and fast.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)"
cd "$ROOT"

echo "# Candidates from the code ($(date -u +%Y-%m-%dT%H:%MZ))"
echo

emit() {
  local label="$1" pattern="$2"
  local hits
  hits="$(grep -rInE "$pattern" \
    --include='*.ts' --include='*.tsx' --include='*.py' \
    --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=e2e \
    --exclude-dir=.git --exclude-dir=__pycache__ \
    frontend backend scripts 2>/dev/null || true)"
  [ -z "$hits" ] && return 0
  echo "## $label"
  # file:line: trimmed message
  echo "$hits" | sed -E 's/^([^:]+:[0-9]+):[[:space:]]*/\1  /' | head -40
  echo
}

# ponytail: excluded — those are deliberate, documented simplifications, not tasks.
emit "TODO / FIXME / HACK / XXX" 'TODO|FIXME|HACK|XXX'

echo "# Next: cross-check against production reliability (redis job errors) and the admin funnel — they outrank TODOs."
