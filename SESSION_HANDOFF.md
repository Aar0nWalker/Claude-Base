# {{PROJECT_NAME}}: durable session handoff

Current as of: 2026-08-03. This file exists so a chat can be cleared safely. It is a compact
working snapshot without secrets — not a replacement for the architecture docs, and not a log of
every edit.

> **Note for whoever bootstraps a project from this template:** the "Current state" section below
> describes the TEMPLATE's own state. Replace it with your project's on the first release.

## What to read in a new session

1. `AGENTS.md` — rules, parallel work, orchestration, quality floor (loads automatically).
2. This file — the current snapshot and unfinished work.
3. `PROJECT.md` / `ARCH.md` / `STACK.md` — what we build, how it is shaped, what it is built with.
4. Only the one skill from `.claude/skills/base/` the task actually needs.

Do not scan the whole repository without a reason: `scripts/agents/codemap.sh <file>`, a targeted
search, and narrow reads.

## Current state (the template itself)

- **`main` at `0fbf3ae`, pushed.** The repository is no longer a SaaS starter: it carries rules,
  the verification pipeline and agent tooling for ANY project — no application code, no stack.
- The previous SaaS starter (FastAPI + Next.js + auth + admin) is preserved on branch
  **`saas-starter-archive`**. Nothing on `main` depends on it.
- Layout: base at the root + two optional modules — `modules/bot` (Telegram task queue) and
  `modules/killswitch` (Clash + Headroom). Either can be deleted whole; the base does not care.
- The gate is deliberately inert here: this repo has no `scripts/ci/zones/`, so
  `scripts/ci/test-gate.sh` refuses to run. That is the designed behaviour, not a bug — a project
  creates its zones during bootstrap.

## Unfinished (next session)

- **End-to-end bootstrap has never been run.** Nobody has cloned this into an empty folder and
  said "make me X" to see where `init.md` sends the agent wrong. That is the one real test of this
  template and it is still outstanding (the owner declined it on 2026-08-03 — ask before spending
  time on it).
- `modules/killswitch/scripts/*` still carry `{{PROD_IP}}` / `{{CLASH_PORT}}` / `{{WSL_*}}`
  placeholders and were never run after the move — the guide is rewritten, the scripts are not
  re-verified.

## Durable gotchas

- The gate is the only verdict — there is no external CI. Its verdict is the `gate green` line,
  never an exit code: a pipe through `tail` returns `tail`'s status, and that has shipped broken
  code before.
- `scripts/ci/test-gate.sh` refuses to run without `scripts/ci/zones/full.sh`. Deliberate: a gate
  that passes because nothing ran is worse than no gate.
- **After moving things, sweep with grep — do not edit from memory.** Twice in one session, edits
  covered only the files that happened to be open, leaving dead plugins, a dead Codex bridge, a
  dropped placeholder step in `init.md`, and four skills still describing the old stack.
- A lockfile-based build (`npm ci`, `poetry.lock`, `Cargo.lock`) breaks on a fresh clone if the
  lockfile is gitignored. It bit this repo; the warning now lives in `.gitignore`.
- `.dockerignore` applies per BUILD CONTEXT, not per repository root — a root-level one does
  nothing for a build whose context is a subdirectory.

## How to continue after a chat reset

1. If no new task is given, ask the user what to continue.
2. Check fresh `git status` and `.agents/wip.md` — this handoff is a snapshot, not a live lock.
3. After changing durable decisions, update this file briefly.
