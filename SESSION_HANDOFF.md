# {{PROJECT_NAME}}: durable session handoff

Current as of: _(update on every refresh)_. This file exists so a chat can be cleared safely.
It is a compact working snapshot without secrets — not a replacement for the architecture docs,
and not a log of every edit.

## What to read in a new session

1. `AGENTS.md` — rules, parallel work, orchestration, quality floor (loads automatically).
2. This file — the current snapshot and unfinished work.
3. `PROJECT.md` / `ARCH.md` / `STACK.md` — what we build, how it is shaped, what it is built with.
4. Only the one skill from `.claude/skills/base/` the task actually needs.

Do not scan the whole repository without a reason: `scripts/agents/codemap.sh <file>`, a targeted
search, and narrow reads.

## Current state

- **Fresh template — the project has not been bootstrapped yet.** Run `init.md`.
  After the first real release, replace this with: what is deployed, on which commit, whether the
  gate is green, and anything running that a new session would not expect.

## Unfinished (next session)

- _(started but not finished; anything waiting on a user decision, with what the options cost)_

## Durable gotchas

Things the next agent would otherwise step on again. Keep it short; delete entries that stop
being true.

- The gate is the only verdict — there is no external CI. Its verdict is the `gate green` line,
  not an exit code.
- `scripts/ci/test-gate.sh` refuses to run until `scripts/ci/zones/full.sh` exists. That is
  deliberate: a gate that passes because nothing ran is worse than no gate.

## How to continue after a chat reset

1. If no new task is given, ask the user what to continue.
2. Check fresh `git status` and `.agents/wip.md` — this handoff is a snapshot, not a live lock.
3. After changing durable decisions, update this file briefly.
