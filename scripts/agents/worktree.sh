#!/usr/bin/env bash
# Per-agent working tree: removes the shared working directory that makes two agents in the
# same files lose each other's edits and coordinate zones through .agents/wip.md.
#
#   scripts/agents/worktree.sh new <name>   — create ../<repo>-wt-<name> on branch wt/<name>
#   scripts/agents/worktree.sh list         — show trees
#   scripts/agents/worktree.sh rm <name>    — remove the tree and its branch
#
# Gates from different trees run in parallel via TEST_GATE_PROJECT_NAME — without it the
# second tree's `down --volumes` kills the first tree's containers.
#
# LIMITATION on Windows: if the deploy path goes through WSL, git inside a worktree does not
# work there — `.git` is a file pointing at a Windows path WSL cannot resolve. Deploy from
# the main tree only. Editing and the Docker gate are unaffected.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

REPO_NAME="$(basename "$ROOT")"
MAIN_BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo main)"

usage() { sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

name_ok() { [[ "$1" =~ ^[a-z0-9][a-z0-9-]{0,30}$ ]]; }

case "${1:-}" in
  new)
    NAME="${2:-}"
    name_ok "$NAME" || { echo "[ERROR] name: lowercase letters/digits/dash, up to 31 chars" >&2; exit 2; }
    DIR="$(cd .. && pwd)/${REPO_NAME}-wt-$NAME"
    [[ -e "$DIR" ]] && { echo "[ERROR] $DIR already exists" >&2; exit 1; }

    git worktree add -b "wt/$NAME" "$DIR" "$MAIN_BRANCH"

    # .env is not in git, but neither the gate nor a local run comes up without it.
    [[ -f .env ]] && cp .env "$DIR/.env"

    cat <<EOF

[OK] tree:    $DIR
     branch:  wt/$NAME

Next, inside it:
  cd "$DIR"
  (cd frontend && npm ci)                                  # only needed for tsc; the gate builds its own in Docker
  TEST_GATE_PROJECT_NAME=gate-$NAME bash scripts/ci/test-gate.sh

Merge back:  git -C "$ROOT" merge wt/$NAME
Remove:      scripts/agents/worktree.sh rm $NAME
EOF
    ;;

  list)
    git worktree list
    ;;

  rm)
    NAME="${2:-}"
    name_ok "$NAME" || { echo "[ERROR] name not given" >&2; exit 2; }
    DIR="$(cd .. && pwd)/${REPO_NAME}-wt-$NAME"
    git worktree remove "$DIR"   # no --force: uncommitted work in the tree is not lost silently
    git branch -d "wt/$NAME" 2>/dev/null \
      || echo "[WARN] branch wt/$NAME not merged — kept (git branch -D to force)"
    echo "[OK] removed: $DIR"
    ;;

  ""|-h|--help) usage 0 ;;
  *) echo "[ERROR] unknown command: $1" >&2; usage 2 ;;
esac
