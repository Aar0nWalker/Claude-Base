#!/usr/bin/env bash
# Hermetic test gate — the only verdict before a release. There is no external CI.
#
#   bash scripts/ci/test-gate.sh                 # full gate
#   GATE_ZONE=backend bash scripts/ci/test-gate.sh
#
# This runner is stack-agnostic. WHAT runs lives in `scripts/ci/zones/<zone>.sh`, written for
# this project at bootstrap (see scripts/ci/zones/README.md). The runner owns the properties
# that are easy to get wrong and expensive to learn the hard way:
#   - a hung run is killed instead of waiting forever;
#   - full logs land on disk before any cleanup can eat them;
#   - the verdict is a LINE (`gate green`), not an exit code that a pipe can swallow;
#   - cheap guards (line endings, "a test is part of the change") run before slow work.
#
# The verdict is the `gate green` line in the output, NOT the exit code of whatever wrapper you
# ran this through: a pipe through `tail`, and `docker wait` on a killed run, both return 0.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
GATE_ZONE="${GATE_ZONE:-full}"
ZONE_SCRIPT="$ROOT/scripts/ci/zones/${GATE_ZONE}.sh"
LOG_DIR="${GATE_LOG_DIR:-$ROOT/.gate-logs}"

# No zone script = no verification. Fail loudly instead of printing a green line: a gate that
# passes because nothing runs is worse than no gate, it manufactures false confidence.
if [[ ! -f "$ZONE_SCRIPT" ]]; then
  echo "[ERROR] no gate zone defined: scripts/ci/zones/${GATE_ZONE}.sh" >&2
  echo "        This project has not set up its verification loop yet." >&2
  echo "        Define it now — see scripts/ci/zones/README.md. Available zones:" >&2
  ls -1 "$ROOT/scripts/ci/zones/" 2>/dev/null | grep '\.sh$' | sed 's/^/          /' >&2 \
    || echo "          (none)" >&2
  exit 2
fi

# ── cheap guards, before anything slow ────────────────────────────────────────────────────
# "A test is part of the change." Range = what a push would ship; empty range still leaves the
# whole-tree checks (stale skips).
BASE_SHA="$(git rev-parse --verify --quiet 'origin/HEAD' 2>/dev/null || true)" \
  bash "$ROOT/scripts/ci/test-lifecycle-check.sh" check

# Windows line endings in .sh. The repo keeps them LF via .gitattributes, but an editor on
# Windows writes the WORKING COPY with CRLF — and the gate reads that copy. Bash trips on the
# first `do\r` and fails with a message about something else entirely.
# The detector is awk with BINMODE, not `grep -lU $'\r'`: msys-bash eats a raw CR inside $(...)
# both in a pattern argument (grep then matches EVERYTHING) and in captured output.
if command -v git >/dev/null 2>&1; then
  crlf_offenders="$(git ls-files -z '*.sh' 2>/dev/null \
    | while IFS= read -rd '' f; do [[ -f "$f" ]] && printf '%s\0' "$f"; done \
    | xargs -0 awk -v BINMODE=1 '/\r/{print FILENAME; nextfile}' 2>/dev/null || true)"
  if [[ -n "$crlf_offenders" ]]; then
    echo "[ERROR] Windows line endings in shell scripts — bash will not parse them:" >&2
    echo "$crlf_offenders" >&2
    echo "        Fix: sed -i 's/\r$//' <file>  (the repo stores them LF)." >&2
    exit 1
  fi
fi

# ── run the zone ──────────────────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${GATE_ZONE}.log"

# A hung run must fail by itself: nobody may be watching, and a stuck gate never un-sticks.
# GATE_TIMEOUT is the budget for the whole zone.
GATE_TIMEOUT="${GATE_TIMEOUT:-1500}"

echo "[TEST] gate zone=$GATE_ZONE (timeout ${GATE_TIMEOUT}s) — $ZONE_SCRIPT"
rc=0
# Output is streamed live AND kept in full on disk: a 120-line tail is never enough to diagnose
# a real failure, and whatever the zone cleans up takes its container logs with it.
timeout --signal=TERM --kill-after=30 "$GATE_TIMEOUT" \
  bash "$ZONE_SCRIPT" 2>&1 | tee "$LOG_FILE" || rc="${PIPESTATUS[0]}"

if [[ "$rc" != "0" ]]; then
  if [[ "$rc" == "124" || "$rc" == "137" ]]; then
    echo "[TEST] GATE HUNG and was killed after ${GATE_TIMEOUT}s (zone=$GATE_ZONE)." >&2
    echo "[TEST] Find what it was waiting on in $LOG_FILE — do not just raise the timeout." >&2
  fi
  echo "[TEST] gate failed (zone=$GATE_ZONE, exit $rc)" >&2
  echo "[TEST] full logs: $LOG_FILE" >&2
  exit "$rc"
fi

echo "[TEST] gate green (zone=$GATE_ZONE)"
