# Skill authoring conventions

Load only when creating or restructuring a skill. Day-to-day work does not need it.

Anything recurring becomes a skill — a file persists between sessions, a prompt dies when the chat
closes. If the user explains the same thing a second time, propose turning it into a skill instead
of waiting to be asked.

A skill has 3 layers, not one prompt:

| Layer | What | Where |
|-------|------|-------|
| Description | When to use the skill (precise) | `SKILL.md` frontmatter |
| Instructions | How to execute | `SKILL.md` body |
| Tools | Scripts, templates, configs | `tools/` |

- **Repeatable logic → code in `tools/`**, not AI recomputation every session. If the skill would
  make you rederive the same thing each time — a search, a tally, a checklist, a report — that is
  a script, and a skill missing it is unfinished.
- A skill that is pure judgement (how to review, how to plan) legitimately has no `tools/`. Don't
  manufacture a script to satisfy the shape.
- Compositional, not monolithic: 3–5 focused skills, each doing one thing; Claude orchestrates them.
- A skill that cannot learn goes stale. If it holds project knowledge, give it a place to record
  new lessons (see `base/debugging-and-error-recovery/tools/bug_ledger.py` and `base/learned-rules/`).
- At the end of a session where a skill was used (or should have been), ask: "What here should be
  baked into the skill permanently, and what was a one-off fix?"

Folder structure:
```
.claude/skills/base/<name>/
├── SKILL.md      # description + instructions
├── tools/        # scripts, templates, configs
└── examples/     # few-shot examples
```

The project skill catalog (and when to load each) is a single list in AGENTS.md → «Rules».
Load only the one skill relevant to the current task.
