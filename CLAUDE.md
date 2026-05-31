# [Project Name] — Claude Instructions

For architecture, data models, and gotchas: read [ARCH.md](ARCH.md).  
For default technologies and stack decisions: read [STACK.md](STACK.md).

## Rules

- Inspect nearby files before editing. Match existing patterns.
- **Changes touching >1 file or >30 lines: write a short plan first.**
- No unrelated refactors. No speculative abstractions. Work only on the requested task.
- **Before changing any function signature: grep all callers, update every call site.**
- After every edit: verify imports resolve. Never leave broken imports.
- Read a file before editing it. Never guess file contents.

## Backward Compatibility

- Changing a schema field: check every endpoint that returns it and every client page that reads it.
- Renaming a model column: write a migration — never edit the model without it.
- Adding a required field to an existing endpoint: make it optional with a default, or version the endpoint.

## Security

- **Never expose PII (phones, emails, tokens, passwords) in API responses or logs.**
- No raw user input in queries — ORM or parameterized statements only.
- **Secrets only from environment variables. Never in source code or logs.**
- Auth check on every protected endpoint — never rely on frontend-only guards.

## Done When

**Bug fix**: root cause identified, fix minimal, imports verified.  
**New feature**: plan written if >1 file or >30 lines, all call sites updated, no broken imports.  
**Before reporting complete**: `tsc --noEmit` (TS) or `python -m py_compile` / pytest (Python) pass.

## Skills

You work as an Anthropic engineer: anything recurring becomes a skill — a file in `.claude/skills/` that persists between sessions. A prompt dies when the chat closes. A skill does not.

**Rule 1. Prompt skills, not me.** If the user explains the same thing a second time — stop and propose turning it into a skill. Don't wait to be asked.

**Rule 2. A skill is 3 layers, not one prompt.**

| Layer | What | Where |
|-------|------|-------|
| Description | When to use the skill (precise) | `SKILL.md` |
| Instructions | How to execute | `SKILL.md` |
| Tools | Scripts, templates, configs | `tools/` |

Empty `tools/` = unfinished skill. Repeatable logic → code in `tools/`, not AI recomputation every session.

**Rule 3. Compositional, not monolithic.** 3–5 focused skills, each does one thing. Claude orchestrates between them.

**Rule 4. Update every session.** At the end of any session where a skill was used or could have been used, ask:

> "What from this session should be baked into the skill permanently, and what was a one-off fix?"

Skill folder structure:
```
.claude/skills/<name>/
├── SKILL.md        # description + instructions
├── tools/          # scripts, templates, configs
└── examples/       # few-shot examples
```

## Off-Limits

<!-- TODO: "never do this" — deferred features, async constraints, rate limit rules, etc. -->
