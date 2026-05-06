# Project Init

You are initializing a new project from templates. Follow the steps below exactly.

---

## Step 1 — Ask questions

Ask the user ALL of the following questions in a single message, numbered list. Wait for answers before doing anything else.

1. **Project name** — used in file headers, script titles, nginx conf name.
2. **Mission** — 1-2 sentences: what does it do and who uses it?
3. **Off-limits** — deferred features or hard constraints for this MVP. (or "none")

---

## Step 2 — Defaults (never ask about these)

Defaults live in `STACK.md` — read it now. Apply silently when a module is needed in a future request. Do not pre-populate ARCH.md with modules that haven't been requested yet.

---

## Step 3 — Fill the templates

Read each file, fill every `TODO` and `[Project Name]` placeholder.

### CLAUDE.md
- Replace `[Project Name]` in the title.
- Fill `## Off-Limits` from Q3. If "none" — write `<!-- none for this project -->`.

### ARCH.md
- **Mission**: Q2 answer.
- **Stack**: leave as TODO comment — filled as modules are added.
- **Layer Map**: leave as TODO — filled as modules are added.
- **Key Modules**: leave placeholder row.
- **Runtime Constraints**: fill universal rules only (no sync sessions, secrets from env, no hardcoded model names). Leave project-specific ones as TODO.
- **Testing**: leave as TODO.

### start.sh and start.bat
- Set `PROJECT_NAME` to Q1 answer.

### install.sh
- Set `PROJECT_NAME` to Q1 answer.
- Set `NGINX_CONF` to slugified project name + `.conf` (lowercase, spaces → hyphens).
- Leave `ENV_OVERRIDES=()` empty — add entries when frontend is added (e.g. `NEXT_PUBLIC_API_URL`, `COOKIE_SECURE`).

### STACK.md
- No changes needed — it is the permanent defaults reference.

### deploy.bat
- No changes needed — user fills `WINSCP_PATH` manually.

---

## Step 4 — Write MVP plan

Write `MVP.md` in the project root. Structure:

```
# [Project Name] — MVP Plan

## Goal
One sentence: what the MVP proves or delivers.

## Scope
Bulleted list of features included in MVP.

## Out of scope
Bulleted list from Q3 (off-limits / deferred).

## Milestones
Ordered list of implementation phases, each with a 1-line description.
```

Base content on Q2 (mission) and Q3 (off-limits). Keep it short and concrete — no fluff.

---

## Step 5 — Confirm and delete

After writing all files, output a single summary:

```
✓ CLAUDE.md
✓ ARCH.md
✓ STACK.md  (defaults reference — do not delete)
✓ start.sh / start.bat
✓ install.sh
✓ MVP.md
— deploy.bat (fill WINSCP_PATH manually)

Project: [name]
```

Then delete this file (`init.md`).
