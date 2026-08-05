# Plugins & tooling

Optional tooling that speeds up agent work in this repo. **Claude plugins live in `~/.claude/`
(user-global): installed once per machine, never committed here.** Everything below is a
convenience — the project works without any of it.

## Global (install once per machine)

| Tool | What it does | Install |
|---|---|---|
| **ponytail** | "Lazy senior dev" mode — forces the simplest solution that actually works, pushes back on over-engineering and speculative abstractions. | Claude Code plugin marketplace: `/plugin install ponytail` |
| **RTK** (Rust Token Killer) | Wraps shell commands and returns a compact form (or passes through untouched) — large token savings on builds, tests and git. | [github.com/rtk-ai/rtk](https://github.com/rtk-ai/rtk); usage in [RTK.md](RTK.md) |
| **Clash Verge Rev** | Proxy client used by the killswitch — all dev traffic goes through it or the network drops. | [github.com/clash-verge-rev/clash-verge-rev](https://github.com/clash-verge-rev/clash-verge-rev) |

## Repo-local (committed here)

- **[RTK.md](RTK.md)** — how RTK is used in this repo.
- **`.claude/`** — rules, commands, skills. The reason this template exists.
- **[modules/killswitch](modules/killswitch/README.md)** — optional: all dev traffic through your
  proxy, or no network at all.
- **[modules/bot](modules/bot/README.md)** — optional: a Telegram task queue for agents.

Not committed, ever: `~/.claude/plugins/*`, `.rtk/`, `.tools/` — all user-global or machine-local.

Deliberately not used: context-compression proxies in front of the model API (Headroom and the
like). On a subscription they save nothing, and the compression drops words from rule files and
tool results. Compression stays at the shell-output layer — that is RTK's job.

## Removing what you don't use

If a project will never use the killswitch or the Telegram worker-bot, delete those scripts and
docs during bootstrap rather than leaving them lying around. Dead tooling reads as live tooling
and costs the next session time — the same reason stale rules are worse than missing ones.
