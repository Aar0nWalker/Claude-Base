# Oridium Code Base

A batteries-included **SaaS starter template** extracted from a production codebase. Clone it,
run `follow init.md`, and you start from a working auth + admin skeleton with deploy, parallel-agent
tooling, and a proxy killswitch already wired — not an empty folder.

It is **generic**: no product domain baked in (no video/AI/marketplace), no billing. Just the
reusable infrastructure every SaaS re-implements.

## What's inside

**Stack** — FastAPI + async SQLAlchemy + Postgres backend · Next.js 16 + React 19 + TS frontend ·
ARQ + Redis worker · Docker Compose + Nginx + certbot. Frontend → backend via a `/backend/*` proxy.

| Area | What you get |
|------|--------------|
| **Auth** | Register / login / verify-email / reset-password, JWT (httpOnly cookie), bcrypt, session invalidation. |
| **Admin** | Users, app settings, editable system-prompts, error log — behind `require_admin` (admin = `ADMIN_EMAIL`). |
| **Backend infra** | Idempotent startup migrations (no Alembic), S3 + local storage, SMTP email, slowapi rate-limit, ARQ worker skeleton, optional Anthropic text helper. |
| **Frontend infra** | App shell, dashboard, profile, admin, minimal landing, toast/confirm/auth providers, UI primitives, design-token CSS, single `apiFetch` wrapper. |
| **Ops** | `install.sh` (one-time server setup: Docker/Nginx/UFW/TLS), `deploy.sh` (rsync + rolling rebuild), `rollback.sh`, `start.sh` (local Docker menu). |
| **Parallel agents** | `.agents/wip.md` registry + `AGENT_SYNC.md` handoff + Telegram worker-bot for a Claude ↔ Codex shared working tree. |
| **Proxy killswitch** | Windows + WSL scripts that force all dev traffic through a proxy (Clash) or lose network — plus optional Headroom token-compression proxy. |
| **Agent config** | `AGENTS.md` / `.claude/CLAUDE.md` (rules, backward-compat, security), permissions, hooks, 7 base engineering skills, `выкати` / `автопилот` commands. |

## Quick start

```bash
# 1. Clone into your new project folder
git clone https://github.com/Aar0nWalker/Oridium-Code-Base .

# 2. Fill in placeholders — open Claude/Codex and run:
follow init.md
#    → asks project name / domain / paths, replaces every {{PLACEHOLDER}},
#      copies .env.example → .env, generates MVP.md, deletes init.md.

# 3a. Local
cp .env.example .env   # (init.md does this) — set JWT_SECRET, POSTGRES_PASSWORD, ADMIN_PASSWORD
bash start.sh          # → 1) Запуск

# 3b. Production server (Debian/Ubuntu, as root)
sudo bash install.sh   # Docker + Nginx + UFW + TLS, then builds images
# then from your machine:
./deploy.sh            # rsync + rolling rebuild
```

The API refuses to boot until `JWT_SECRET` is changed from the default — set it in `.env`.

## Layout

```
├── AGENTS.md  .claude/CLAUDE.md      # agent rules (shared) + Claude specifics
├── STACK.md  ARCH.md                 # stack defaults + architecture map
├── RTK.md  PLUGINS.md                # tooling: RTK, ponytail, caveman, Headroom, uv
├── init.md                           # one-time placeholder-fill flow (delete after)
├── .env.example                      # env keys (no secrets) — copy to .env
├── docker-compose.yml                # web · api · worker-fast · redis · db · worker-bot
├── install.sh  deploy.sh  rollback.sh  start.sh
├── backend/   FastAPI app (app/{main,db,models,routers/*,deps,storage,email,worker,ai_text})
├── frontend/  Next.js app (app/, components/, lib/, styles/)
├── scripts/   worker-bot + killswitch + headroom
├── docs/      telegram-worker-bot.md · proxy-killswitch.md
├── .agents/   wip.md registry + worker-bot/ skeleton
└── .claude/   settings.json · commands/ · skills/base/
```

## Concepts worth knowing

- **Migrations** are idempotent and run on every boot (`backend/app/db.py`): `create_all` + a list of
  `ALTER ... IF NOT EXISTS`. To change the schema, edit `models.py` and append one more idempotent
  statement. No Alembic.
- **Parallel agents** share one working tree — before editing, claim a row in `.agents/wip.md`; commit
  only your own files; deploy is exclusive. Full protocol in [AGENTS.md](AGENTS.md).
- **Skills** live in `.claude/skills/base/` — load the one relevant to the task (planning, implementation,
  debugging, security, review, frontend, autopilot).
- **Killswitch** (optional) forces dev traffic through a proxy so nothing leaks direct — see
  [scripts/KILLSWITCH.md](scripts/KILLSWITCH.md).

## What this template deliberately omits

Billing, and any product/domain logic — add those as new routers + models + migrations on top of the
auth/admin base, following the backward-compatibility rules in AGENTS.md. AI is limited to an optional
Anthropic text helper (`backend/app/ai_text.py`); wire in image/video/other providers per project.
