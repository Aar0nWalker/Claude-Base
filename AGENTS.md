# {{PROJECT_NAME}} — Agent Instructions

For architecture and gotchas: read [ARCH.md](ARCH.md).
For default technologies and stack decisions: read [STACK.md](STACK.md).
For token-optimized shell commands, prefer [RTK.md](RTK.md) when `rtk` is available.

## Project Map

Stack: Next.js 16 + React 19 + TS frontend, FastAPI + async SQLAlchemy + Postgres backend,
ARQ+Redis worker, Docker Compose. Frontend calls backend via `/backend/*` rewrite proxy.

**Frontend** (`frontend/`)
- `app/(auth)/` — login / register / verify-email / reset-password.
- `app/(app)/` — authed shell: `dashboard`, `profile`, `admin`. Shell = `layout.tsx` + `components/layout/*`.
- `app/page.tsx` — landing. `app/globals.css` — design tokens.
- `components/` — `providers.tsx` (toast + confirm + auth), `toast-provider.tsx`, `confirm-provider.tsx`, `ui/*` primitives.
- `lib/api.ts` — fetch wrapper. `lib/auth-context.tsx` — session. `lib/data.ts` — small shared helpers.

**Backend** (`backend/app/`)
- `main.py` — lifespan: idempotent migrations + seed settings/admin, router registration, CORS/CSRF/body-limit.
- `db.py` — startup migrations via `create_all` + idempotent `ALTER ... IF NOT EXISTS` (no Alembic).
- `models.py` — `User`, `SystemPrompt`, `AppSetting`, `ErrorLog`, `UserActionEvent`, `PendingMediaDelete`.
- `routers/` — `auth.py` (register/login/verify/reset + JWT), `admin.py` (users/settings/prompts/errors), `tracking.py`.
- `deps.py` (JWT auth), `storage.py` (S3 + local fallback), `email.py` (SMTP), `limiter.py` (slowapi), `worker.py` (ARQ skeleton), `ai_text.py` (optional Anthropic text helper).

**Where things live**: schema changes → edit `models.py` + add idempotent migration in `db.py`.
Admin-editable prompts/settings → `SystemPrompt`/`AppSetting` seeded on startup. Star/credit/billing:
not included in the base — add per-project.

## Parallel Work: multiple agents (shared working tree)

If two agents (e.g. Claude + Codex) edit the SAME working tree, uncoordinated work loses edits.
Non-negotiable protocol:

1. **WIP registry `.agents/wip.md`**: before starting any task that edits files, ADD a row
   (agent, task, files/zones, started); REMOVE it when done. Before editing a file, check the
   registry — if another agent's row covers it, do NOT edit; surface the conflict.
2. **Commit only your own files**: always `git add <explicit paths>`, never `git add -A`/`.`.
   Before committing, check `git status` — leave out unrelated (other agent's WIP) changes and say so.
3. **Deploy is exclusive**: `deploy.sh` rsyncs the WORKING COPY, not a commit — it would ship
   another agent's unfinished WIP. Before deploying, check `.agents/wip.md` and `git status` for
   foreign uncommitted changes; if found, ask before proceeding.
4. **Zones on claim**: declare your file zone in the wip row at claim time. If the zone is taken,
   surface the conflict immediately instead of silently editing.

Cross-agent handoff notes live in `AGENT_SYNC.md` — update only when durable context is useful;
never put secrets or long logs there. The Telegram worker-bot (`.agents/worker-bot/`, `scripts/worker_bot.py`)
can feed a live task queue to agents — see [docs/telegram-worker-bot.md](docs/telegram-worker-bot.md).

## Rules

- Communication: answer in Russian by default; keep replies short and thesis-style.
- Inspect nearby files before editing. Match existing patterns.
- Changes touching more than 1 file or more than 30 lines: write a short plan first.
- No unrelated refactors. No speculative abstractions. Work only on the requested task.
- Before changing any function signature: search all callers and update every call site.
- After every edit: verify imports resolve. Never leave broken imports.
- Read a file before editing it. Never guess file contents.
- Prefer `rtk <command>` when `rtk` exists on PATH; otherwise run the underlying command directly.

## Backward Compatibility

- Changing a schema field: check every endpoint that returns it and every client page that reads it.
- Renaming a model column: write a migration in `db.py`. Never edit the model without it.
- Adding a required field to an existing endpoint: make it optional with a default, or version it.

## Security

- Never expose PII (phones, emails, tokens, passwords) in API responses or logs.
- No raw user input in queries. Use ORM or parameterized statements only.
- Secrets only from environment variables. Never in source code or logs.
- Auth check on every protected endpoint. Never rely on frontend-only guards.

## Done When

**Bug fix**: root cause identified, fix minimal, imports verified.
**New feature**: plan written if more than 1 file or more than 30 lines, all call sites updated, no broken imports.
**Before reporting complete**: `tsc --noEmit` for TS changes, or `python -m py_compile` / pytest for Python, pass when practical.
