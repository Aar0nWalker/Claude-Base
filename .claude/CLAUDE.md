# {{PROJECT_NAME}} — Claude Instructions

Shared context — project map, parallel-work protocol (`.agents/wip.md`), rules, backward
compatibility, security, done-when — is canonical in AGENTS.md and imported below.

@../AGENTS.md

For architecture and gotchas: read [ARCH.md](../ARCH.md).
For default technologies and stack decisions: read [STACK.md](../STACK.md).

## Claude-Specific Rules

- **Parallelize when possible**: for independent, isolatable subtasks (codebase search,
  affected-file analysis, second-opinion review, disjoint edits) launch subagents (Agent tool) —
  send them in one message to run concurrently. Keep integration, final review, tests, deploy,
  and git in the main agent.
- **Never run tests that spend money on paid/neural-net APIs unless the user explicitly allows it.**
- **Command shortcuts**: `выкати` = deploy to production, check health/logs, fix errors, then commit
  + push if green (see `.claude/commands/выкати.md`). `не деплой` = local edits/checks, no prod
  deploy; `не пуш` = no git commit/push; `запуш` = verify then commit + push (don't touch unrelated changes).

## Skills

Anything recurring becomes a skill — a file in `.claude/skills/` that persists between sessions.
A prompt dies when the chat closes; a skill does not.

**Rule 1. Prompt skills, not me.** If the user explains the same thing twice — propose turning it
into a skill. Don't wait to be asked.

**Rule 2. A skill is 3 layers**: Description (when to use) + Instructions (how) in `SKILL.md`,
plus reusable `tools/` (scripts/templates). Empty `tools/` = unfinished skill.

**Rule 3. Compositional, not monolithic.** 3–5 focused skills; Claude orchestrates between them.

**Rule 4. Update every session** a skill was (or could have been) used: "what should be baked in
permanently, and what was a one-off?"

Skill folder: `.claude/skills/<name>/{SKILL.md, tools/, examples/}`.

Current base skills (load only the relevant one, never all at once):
- `.claude/skills/base/planning-and-task-breakdown/SKILL.md` — split work into small agent-ready tasks.
- `.claude/skills/base/incremental-implementation/SKILL.md` — implement small verified slices.
- `.claude/skills/base/debugging-and-error-recovery/SKILL.md` — broken builds, deploys, queues, API, UI bugs.
- `.claude/skills/base/security-and-hardening/SKILL.md` — auth, admin, external APIs, uploads.
- `.claude/skills/base/frontend-ui-engineering/SKILL.md` — UI, landing, app shell, screenshots.
- `.claude/skills/base/code-review-and-quality/SKILL.md` — review before deploy/push.
- `.claude/skills/base/autopilot/SKILL.md` — self-driving режим (`/автопилот`): autonomous small verified slices when there are no explicit tasks.

## Claude Files

- `.claude/CLAUDE.md` (this file), `.claude/frontend/CLAUDE.md`, `.claude/settings.json`,
  `.claude/commands/`, `.claude/skills/base/`.
