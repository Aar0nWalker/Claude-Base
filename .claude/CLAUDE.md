# {{PROJECT_NAME}} — Claude Instructions

Shared context — project map, parallel-work protocol (`.agents/wip.md`), orchestration +
automatic scaling, quality floor, backward compatibility, security, done-when — is canonical in
AGENTS.md and imported below. The planning model orchestrates; execution subagents run on the
cheaper/faster model (see AGENTS.md → «Orchestration»).

@../AGENTS.md

For architecture and gotchas: read [ARCH.md](../ARCH.md).
For default technologies and stack decisions: read [STACK.md](../STACK.md).

## Claude-Specific Rules

- **This session is the planner and orchestrator.** Apply the shared automatic scaling without
  asking the user. Do trivial, sequential, tightly coupled and sensitive work directly; keep the
  global plan, integration, security/payment/DB decisions, final scoped verification, release
  gate, git and deploy. For genuinely disjoint zones launch **your own subagents** (Agent tool,
  `model: sonnet`): one helper only for one independent support track, 2–3 for 2–3 independent
  zones, 4–5 only for a large task with clearly disjoint ownership. Never create work to fill
  slots or spin up parallel agents for one goal.
- Before delegated edits, claim exact `.agents/wip.md` zones. Read-only reconnaissance needs no
  claim but must be rechecked if relevant files change. Failures caused by the current change are
  fixed and retested in the same task. After 3 failed iterations on one delegated task, take over.
- Subagents suit both bounded read-only reconnaissance and disjoint repository edits, under the
  same count thresholds. Children verify their slices; you verify the integrated result.
- **Never run tests that spend money on paid/AI APIs unless the user explicitly allows it.**
- **Command shortcut `выкати`**: deploy to production, check server health/logs, fix any errors,
  then commit + push only if checks pass. Full procedure: `.claude/commands/выкати.md`.
- **Command shortcut `контекст`**: read project context (AGENTS/SESSION_HANDOFF/ARCH/STACK) and
  answer only «Ознакомился, готов работать». Full procedure: `.claude/commands/контекст.md`.
- **Command shortcut `запакуй`**: archive the current chat into `chat-archive/` and refresh
  `SESSION_HANDOFF.md` for the next agent. Full procedure: `.claude/commands/запакуй.md`.
- **Command shortcuts**: `не деплой` / `не выкатывай` = local edits and checks but no production
  deploy; `не пуш` = no git commit/push; `запуш` = verify changes, then commit + push (don't touch
  unrelated changes — say so if present).

## Skills

Anything recurring becomes a skill in `.claude/skills/` — if the user explains the same thing
twice, propose one instead of waiting to be asked. The skill catalog and load rules live in
AGENTS.md → «Rules»; load only the one skill relevant to the current task, never all at once.
Authoring conventions (3 layers, `tools/`, folder layout) are in
[.claude/skills/AUTHORING.md](skills/AUTHORING.md) — read on demand.

## Claude Files

- `.claude/CLAUDE.md` (this file), `.claude/settings.json`, `.claude/commands/`,
  `.claude/skills/base/` (+ `AUTHORING.md`).

Nested `CLAUDE.md` files: if one area of the project needs its own standing rules (a UI folder,
a generated-code folder), put a `CLAUDE.md` inside that directory so it loads only when work
happens there. Do not grow this file for something that concerns one folder.
