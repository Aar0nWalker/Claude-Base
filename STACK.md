# Stack Defaults

Default technologies for {{PROJECT_NAME}}. Use these when adding a module unless a task says otherwise.

| Module / service | Technology |
|-----------------|------------|
| Backend | Python 3.12 + FastAPI + async SQLAlchemy 2.0 + asyncpg |
| Database | PostgreSQL 16 |
| Frontend | Node 20 + Next.js 16 (App Router, standalone, Turbopack) + React 19 + TypeScript |
| Styles | CSS variables (no Tailwind); icons via `lucide-react` |
| Background worker | ARQ + Redis (`worker-fast`, queue `arq:queue`) |
| Cache / queue | Redis 7 |
| Auth | JWT single access token (`get_current_user`), bcrypt password hashing |
| Email | SMTP via `aiosmtplib` (verification / password reset) |
| File storage | S3-compatible via `aioboto3`; fallback — local FS `/storage` (Docker volume) |
| Rate limiting | slowapi |
| AI text (optional) | Anthropic Claude via `app/ai_text.py` (only if `ANTHROPIC_API_KEY` set) — default model `claude-opus-4-8` |
| Infra | Docker Compose + Nginx + certbot (TLS) |
| API port | 8000 (container, localhost-bound) |
| Web port | 3000 (container) / 3001 (host) |
| Nginx routing | `/` → Web:3001; Next proxies `/backend/*` → api:8000 |
| Migrations | idempotent startup migrations in `db.py` (`create_all` + `ALTER ... IF NOT EXISTS`), no Alembic |
| Test runner | pytest + pytest-asyncio (backend) |

## Rules

- Don't hardcode technology/model names — read from env / constants.
- No sync DB sessions in async context.
- Secrets only from env vars, never in code or logs.
- Never expose PII (phones, emails, tokens) in API responses or logs.
- Raw user input only through the ORM / parameterized statements.
