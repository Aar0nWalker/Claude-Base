#!/usr/bin/env bash
# Rotate local agent transcripts in .agents/sessions (gitignored — they grow to hundreds of
# megabytes if nobody trims them). Keeps the 3 newest per agent; the second-newest survives
# only while it is small enough to be worth loading for context continuation.
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.agents/sessions" 2>/dev/null && pwd)" || exit 0
for dir in "$BASE"/* "$BASE"; do
  [ -d "$dir" ] || continue
  cd "$dir" 2>/dev/null || continue
  for pat in claude codex; do
    # everything older than the newest 3 — delete
    ls -t "${pat}"-*.jsonl 2>/dev/null | tail -n +4 | while read -r f; do rm -f -- "$f"; done
    # keep the older survivors only while under 50 MB
    ls -t "${pat}"-*.jsonl 2>/dev/null | tail -n +2 | while read -r f; do
      [ "$(stat -c %s -- "$f" 2>/dev/null || echo 0)" -gt 52428800 ] && rm -f -- "$f"
    done
  done
done
exit 0
