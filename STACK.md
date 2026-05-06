# Stack Defaults

When adding a module, use these technologies unless the user specifies otherwise.

| Module / service | Default |
|-----------------|---------|
| Backend | FastAPI + async SQLAlchemy 2.0 + asyncpg |
| Database | PostgreSQL |
| Frontend | Next.js 14 (App Router) + TypeScript |
| Background workers | asyncio tasks via `asyncio.ensure_future` in the backend service |
| Cache / sessions | Redis |
| File storage | S3-compatible (env-configured) |
| Infra | Docker Compose |
| API port | 8000 |
| Web port | 3000 |
| Nginx routing | `/api/` → API:8000, `/` → Web:3000 |
| JWT | access 30 min, refresh 30 days |
| Test runner | pytest (backend), vitest (frontend) |

## Rules

- Never hardcode technology names in source — always from env vars where applicable.
- No sync DB sessions in async context.
- Secrets always from environment variables, never in source code.
