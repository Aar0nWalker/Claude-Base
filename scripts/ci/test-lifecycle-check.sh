#!/usr/bin/env bash
# "A test is part of the change, not follow-up work" — enforced, not just documented.
# Runs inside the gate before anything slow, so it costs seconds.
#
#   bash scripts/ci/test-lifecycle-check.sh check
#   BASE_SHA=origin/main bash scripts/ci/test-lifecycle-check.sh check
#
# Two kinds of check:
#   range checks — over what a push would ship (needs BASE_SHA; skipped when empty)
#   tree checks  — over the whole working tree, always run
#
# Language-agnostic by pattern. If your stack names tests differently, widen TEST_RE below —
# that is a one-line edit, and a wrong pattern here makes the guard silently useless.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
MODE="${1:-check}"
[[ "$MODE" == "check" ]] || { echo "usage: test-lifecycle-check.sh check" >&2; exit 2; }

command -v git >/dev/null 2>&1 || { echo "[LIFECYCLE] no git — skipped"; exit 0; }

fail=0
note() { echo "[LIFECYCLE] $*" >&2; }

# Anything that carries behaviour. Config, styles, docs and lockfiles are excluded on purpose:
# they do not need a test, and demanding one teaches everyone to bypass the guard.
SRC_RE='\.(py|ts|tsx|js|jsx|mjs|go|rs|rb|java|kt|cs|php|swift|c|cc|cpp|h|hpp|ex|exs|scala|dart)$'
# Test files, by the conventions of the common ecosystems.
TEST_RE='(^|/)(tests?|spec|__tests__|e2e)/|(^|/)test_[^/]+\.|[._-](test|spec)\.[a-z]+$|_test\.[a-z]+$'

# ── range checks ──────────────────────────────────────────────────────────────────────────
if [[ -n "${BASE_SHA:-}" ]] && git rev-parse --verify --quiet "$BASE_SHA" >/dev/null 2>&1; then
  changed="$(git diff --name-only "$BASE_SHA"...HEAD 2>/dev/null || true)"

  if [[ -n "$changed" ]]; then
    src_changed="$(echo "$changed" | grep -E "$SRC_RE" | grep -Ev "$TEST_RE" || true)"
    test_changed="$(echo "$changed" | grep -E "$TEST_RE" || true)"

    if [[ -n "$src_changed" && -z "$test_changed" ]]; then
      # Escape hatch that leaves a trace. A silent env-var bypass is deliberately not offered:
      # the reason has to be written down where a reviewer sees it.
      if git log --format=%B "$BASE_SHA"..HEAD 2>/dev/null | grep -qiE '^no-test:'; then
        note "behaviour changed without a test — allowed by a 'no-test:' commit trailer"
      else
        note "behaviour changed but no test did:"
        echo "$src_changed" | sed 's/^/            /' >&2
        note "Add or update the test in the same change. If genuinely untestable, say why in"
        note "the commit message on its own line: 'no-test: <reason>'."
        fail=1
      fi
    fi

    # A deleted test whose feature is still alive means coverage was dropped, not removed.
    while IFS=$'\t' read -r status path; do
      [[ "$status" == "D" ]] || continue
      [[ "$path" =~ $TEST_RE ]] || continue
      note "test file deleted: $path"
      note "Removing a test is fine only when its functionality is gone — say so in the commit."
      fail=1
    done < <(git diff --name-status --diff-filter=D "$BASE_SHA"...HEAD 2>/dev/null || true)
  fi
fi

# ── tree checks ───────────────────────────────────────────────────────────────────────────
# A skipped test without a stated reason is a test quietly switched off. Never delete, weaken
# or skip a test to get to green: one failing after your edit did its job.
test_files="$(git ls-files 2>/dev/null | grep -E "$TEST_RE" || true)"
if [[ -n "$test_files" ]]; then
  # pytest: skip/xfail without reason=
  py_skips="$(echo "$test_files" | grep -E '\.py$' \
    | xargs -r grep -nE '@pytest\.mark\.(skip|xfail)\b' 2>/dev/null | grep -vE 'reason\s*=' || true)"
  # JS/TS runners, Go, Rust
  other_skips="$(echo "$test_files" | grep -vE '\.py$' \
    | xargs -r grep -nE '\b(test|it|describe)\.(skip|fixme)\b|\bx(it|describe)\(|\bt\.Skip\(|#\[ignore\]' 2>/dev/null || true)"

  if [[ -n "$py_skips$other_skips" ]]; then
    note "disabled test — re-enable it, or delete it together with its feature:"
    { [[ -n "$py_skips" ]] && echo "$py_skips"; [[ -n "$other_skips" ]] && echo "$other_skips"; } \
      | sed 's/^/            /' >&2
    fail=1
  fi
fi

if [[ "$fail" != "0" ]]; then
  note "FAILED — a test failing after your edit did its job; never weaken it to get green."
  exit 1
fi
echo "[LIFECYCLE] ok"
