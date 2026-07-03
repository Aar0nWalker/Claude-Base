# Architecture — {{PROJECT_NAME}}

Generic SaaS base: FastAPI backend + Next.js frontend + Postgres + Redis/ARQ worker, all in Docker
Compose behind Nginx. This file is the map; keep it current as the project grows.

## Request flow

```
Browser ──HTTPS──▶ Nginx ──┬─▶ / ............▶ Web (Next.js :3001)
                           └─▶ (Next rewrites /backend/* ─▶ API :8000)
Web (Next standalone) ──/backend/*──▶ API (FastAPI :8000) ──▶ Postgres / Redis
Worker (ARQ) ◀── Redis queue ── API enqueues jobs
```

- Frontend talks to the backend ONLY through the `/backend/*` rewrite proxy (`next.config.ts`) —
  no separate API host, no CORS in the browser path. `lib/api.ts` is the single fetch wrapper.
- API and Web host ports bind to `127.0.0.1` (Docker bypasses UFW); Nginx is the only public surface.

## Backend (`backend/app/`)

- **`main.py`** — FastAPI app + lifespan. On startup: refuse to boot if `JWT_SECRET` is default →
  run migrations (`db.create_tables`) → seed app settings + admin user (from `ADMIN_EMAIL`/`ADMIN_PASSWORD`)
  → clear maintenance flag → start the backup loop. Registers routers, CORS/CSRF, body-size limit.
- **`db.py`** — engine + async session factory. Migrations are idempotent: `Base.metadata.create_all`
  creates missing tables, then a flat list of `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` /
  `CREATE INDEX IF NOT EXISTS` runs every boot. **To change the schema: edit `models.py`, then append
  one more idempotent statement here.** No Alembic.
- **`models.py`** — `User`, `SystemPrompt` (admin-editable prompt framework), `AppSetting` (key/value
  settings), `ErrorLog`, `UserActionEvent` (analytics), `PendingMediaDelete` (storage-cleanup retry).
- **`routers/`** — `auth.py` (register / login / verify-email / reset-password / JWT), `admin.py`
  (users, app settings, system prompts, error log — behind `require_admin`), `tracking.py` (action events).
- **`deps.py`** — JWT decode, `get_current_user`, `require_admin`. **`storage.py`** — S3 + local
  fallback. **`email.py`** — SMTP. **`limiter.py`** — slowapi. **`worker.py`** — ARQ worker skeleton
  (`WorkerSettings` / `FastWorkerSettings`, one `example_task`). **`ai_text.py`** — optional Anthropic helper.

## Frontend (`frontend/`)

- **App Router**, standalone output. `app/(auth)/` = login/register/verify/reset; `app/(app)/` =
  authed shell (dashboard, profile, admin) gated client-side by `lib/auth-context.tsx` (`useAuth`);
  `app/page.tsx` = landing.
- **`components/providers.tsx`** composes toast + confirm + auth providers. UI primitives in
  `components/ui/*`; shell chrome in `components/layout/*`. Design tokens in `app/globals.css`.
- No SSR auth guard / middleware — auth is client-side via the auth context. Add edge middleware only
  if you need SSR-protected routes.

## Infra & ops

- **`docker-compose.yml`** — services `web`, `api`, `worker-fast`, `redis`, `db`, `worker-bot` (optional).
- **`install.sh`** — one-time server setup (Docker, Nginx, UFW, TLS, localhost port binding).
- **`deploy.sh`** — rsync working copy → server, then `start.sh --rebuild` (rolling rebuild). **`rollback.sh`** — switch to `:rollback` images.
- **`start.sh`** — local Docker control menu + `--rebuild` / `--rollback`.
- **Parallel work** (multiple agents): `.agents/wip.md` registry, `AGENT_SYNC.md` handoff, Telegram
  worker-bot (`scripts/worker_bot.py`) — see AGENTS.md and [docs/telegram-worker-bot.md](docs/telegram-worker-bot.md).
- **Proxy killswitch** (dev machine, optional): route all dev traffic through a proxy or lose network —
  see [scripts/KILLSWITCH.md](scripts/KILLSWITCH.md) and [docs/proxy-killswitch.md](docs/proxy-killswitch.md).

## Gotchas

- Startup migrations run on every boot — they must stay idempotent. Never write a one-shot ALTER.
- `JWT_SECRET` must differ from the default or the API refuses to start (guard in `main.py`).
- The base has NO billing and NO domain models beyond auth/admin/settings — add your product surface
  as new routers + models + migrations, keeping backward-compat rules (AGENTS.md) in mind.
