---
name: debugging-and-error-recovery
description: Use when {{PROJECT_NAME}} has a failing build, broken deploy, production error, queue issue, or unexpected UI/API behavior.
---

# Debugging And Error Recovery

Use a narrow root-cause loop:

1. Reproduce or locate the failing path.
2. Read the code that owns that path.
3. Check logs/errors before guessing.
4. Fix the shared root cause, not one visible symptom.
5. Add a guard only where it prevents recurrence.
6. Re-run the smallest relevant verification.

{{PROJECT_NAME}} hotspots:

- background jobs: `backend/app/worker.py`, `backend/app/queues.py`;
- auth: `backend/app/routers/auth.py`, `backend/app/deps.py`, `frontend/lib/api.ts`, `frontend/lib/auth-context.tsx`;
- admin/settings: `backend/app/routers/admin.py`, `frontend/app/(app)/admin/`;
- deploy: `deploy.sh`, `start.sh`, `rollback.sh`, `docker-compose.yml`.

Do not hide errors that should fail loudly in production.
