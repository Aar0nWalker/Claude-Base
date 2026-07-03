# Project Init

You are initializing a new project from this base template. Do the following, then delete this file.

## 1. Ask the user (one short round)

Collect these values. Offer sensible defaults; only `PROJECT_NAME` is truly required.

| Placeholder | Meaning | Default |
|-------------|---------|---------|
| `{{PROJECT_NAME}}` | Human name, e.g. "Acme" | — (ask) |
| `{{PROJECT_SLUG}}` | lowercase slug (image tags, db, cookies), e.g. "acme" | slugify(PROJECT_NAME) |
| `{{PROJECT_TAGLINE}}` | one-line landing tagline | ask or leave generic |
| `{{DOMAIN}}` | production domain, e.g. "acme.com" | `PROJECT_SLUG.com` |
| `{{PROD_IP}}` | production server IP (deploy target) | ask or `CHANGE_ME` |
| `{{PROJECT_PATH_WIN}}` | Windows repo path (killswitch/bot) | current dir, Windows form |
| `{{PROJECT_PATH_WSL}}` | WSL repo path (`/mnt/...`) | current dir, WSL form |
| `{{CLASH_PORT}}` | local proxy port (killswitch) | `7897` |
| `{{WSL_DISTRO}}` | WSL distro name | `Ubuntu` |
| `{{WSL_USER}}` | WSL username | ask |

Also ask the mission / MVP scope in 1-2 sentences (for `MVP.md`).

The parallel-work, Telegram-bot, and killswitch placeholders (`PROD_IP`, `PROJECT_PATH_*`,
`CLASH_PORT`, `WSL_*`) only matter if the user will use those features. If not, tell them they can
leave the defaults and fill them later.

## 2. Replace placeholders everywhere

Replace every `{{...}}` occurrence across ALL files (root, `backend/`, `frontend/`, `scripts/`,
`docs/`, `.claude/`, `.env.example`, `docker-compose.yml`). Verify none remain:

```bash
grep -rl "{{" . --exclude-dir=.git
```

## 3. Set up env

Copy `.env.example` → `.env`, generate a strong `JWT_SECRET`, set `POSTGRES_PASSWORD` and
`ADMIN_PASSWORD`. Remind the user `.env` is gitignored and must never be committed.

## 4. Generate `MVP.md`

Write `MVP.md`: the mission, the MVP feature list, and a short phased implementation plan (what to
build on top of the auth/admin base first). Keep it concrete and small.

## 5. Clean up

- Delete this `init.md`.
- Delete `REWRITE-PLAN.md` if present (it documents how this template was built, not your project).
- Optionally reset git history for a fresh start: `Remove-Item -Recurse -Force .git; git init` (PowerShell)
  or `rm -rf .git && git init`.

Then tell the user the next step: `sudo bash install.sh` on the server, or `bash start.sh` locally.
