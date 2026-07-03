# Plugins & Tooling

Recommended Claude Code / agent tooling for working in this repo. **Claude plugins live in
`~/.claude/` (user-global) — they are installed once per machine and are NOT committed here.**
This file lists what to install and what is repo-local.

## Global (install once per machine)

| Tool | What it does | Install / enable |
|------|--------------|------------------|
| **RTK** (Rust Token Killer) | Wraps shell commands and returns a compact form (or passes through) — big token savings on builds/tests/git. | See [github.com/rtk-ai/rtk](https://github.com/rtk-ai/rtk); or use the repo-local wrapper `.tools/bin/rtk` (see [RTK.md](RTK.md)). |
| **ponytail** | "Lazy senior dev" mode — forces the simplest solution that works, anti-over-engineering. | Claude Code plugin marketplace: `/plugin install ponytail`. |
| **caveman** | Compresses Claude's textual replies without losing technical precision. | [github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman). |
| **karpathy-skills** | Global `CLAUDE.md` skill set that improves coding behavior. | [github.com/forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills). |
| **uv / uvx** | Fast Python runner — local fallback when Docker isn't available (e.g. `uv run pytest`). | [astral.sh/uv](https://astral.sh/uv). Repo-local copies may live in `.tools/bin/`. |

These are developer conveniences — the project builds and runs without any of them.

## Repo-local (committed here)

- **`RTK.md`** — how RTK is used in this repo.
- **`.claude/`** — permissions, hooks, and the base skills under `.claude/skills/base/`.
- **Headroom killswitch wiring** — `scripts/start-headroom.sh`, `scripts/killswitch-*.ps1`,
  `scripts/wsl-killswitch.sh`, [scripts/KILLSWITCH.md](scripts/KILLSWITCH.md). Optional; enable only if
  you want all dev traffic forced through a proxy (see [docs/proxy-killswitch.md](docs/proxy-killswitch.md)).

## Headroom (optional token-compression proxy)

Headroom is an MCP/HTTP proxy that compresses model requests and can route agent traffic through your
proxy (Clash). Enable it if you run the killswitch:

- Point Claude/Codex at it via `ANTHROPIC_BASE_URL=http://127.0.0.1:8788` (leave empty for direct API).
- Start it with `scripts/start-headroom.sh`.
- It is user-local infra — `.headroom/`, `.tools/`, `.venv-headroom/` are gitignored.

## Not committed (gitignored)

`~/.claude/plugins/*`, `.headroom/`, `.tools/`, `.venv-headroom/`, `.rtk/` — all user-global or
machine-local; never pushed with the template.
