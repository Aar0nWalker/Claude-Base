#!/usr/bin/env bash
# codemap — symbol map of a monster file: symbol → line number.
# Jump straight to the function with Read offset/limit instead of reading the whole file.
#
# Usage: bash scripts/agents/codemap.sh backend/app/worker.py
#        bash scripts/agents/codemap.sh 'frontend/app/(app)/dashboard/page.tsx'
set -euo pipefail
f="${1:?usage: codemap.sh <file>}"
[ -f "$f" ] || { echo "no file: $f" >&2; exit 1; }
case "$f" in
  *.py)
    grep -nE '^[[:space:]]*(async def|def|class) ' "$f" ;;
  *.ts|*.tsx|*.js|*.jsx)
    grep -nE '^[[:space:]]*(export )?(async )?function |^[[:space:]]*const [A-Za-z0-9_]+ = (async )?\(|^[[:space:]]*(export )?(default )?function ' "$f" ;;
  *)
    grep -nE '^[[:space:]]*(async def|def|class|function|export) ' "$f" ;;
esac
echo "--- total lines: $(wc -l < "$f")"
