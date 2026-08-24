---
name: autopilot
description: Autonomous self-improvement loop for {{PROJECT_NAME}}. Use when the user has run `/автопилот` (or said "autopilot", "develop yourself") and there are no explicit tasks — the agent finds improvements itself, makes small verified slices, ships green changes to production, and reports back while the user is away.
---

# Autopilot — self-driving mode

Goal: while there are no clear tasks, continuously and **safely** improve the service. The
user started the machine, ran the command, and left — autopilot must work on its own,
break nothing in production, and leave a clear trail (Telegram, if wired up, and the log).

Deploy policy (decide once per project and keep it here): **ship to production every cycle
if everything is green.** Enforced by the guardrails below.

## One cycle

0. **Keepalive.** `bash modules/bot/scripts/keepalive.sh` (only if the bot module is installed) —
   restart the bot loop if it died, check network. If the network is down, end the cycle without
   doing work — the next tick resumes on its own. Nothing is lost: the backlog and git are
   persistent.
1. **Explicit tasks first.** `./modules/bot/scripts/worker-bot.sh queue` (if the Telegram worker-bot is
   set up). Open tasks exist → do them, autopilot yields. Only pull from the backlog when
   the queue is empty.
2. **Pick work.** Top unclaimed item in `.agents/autopilot/backlog.md` ("Ready" section). If
   empty, refresh candidates: `bash .claude/skills/base/autopilot/tools/gather-signals.sh`,
   pick the highest-value one (production reliability > funnel/UX friction from
   analytics > copy/polish).
3. **Claim + zone.** Add a row to `.agents/wip.md` (agent, files/zones). If the zone overlaps
   an active row from another agent, pick a different item.
4. **Small slice.** Plan first if it touches more than 1 file or more than 30 lines; edit in
   the style of the surrounding code; no speculative abstractions. One item per cycle.
5. **Verify.** Narrow check for the changed zone: `bash scripts/ci/check.sh <zone>`.
   Never spend money on paid AI APIs during checks (project rule).
6. **Deploy if green.** Only if checks pass AND the tree is clean of foreign changes:
   - Check `.agents/wip.md` for another agent's active row and `git status` for foreign
     uncommitted changes. **Foreign WIP present → do NOT release** (a deploy that ships the
     working copy would carry the other agent's unfinished work): commit your own slice with
     explicit paths, note "release deferred — foreign WIP", move on.
   - Clean → release per `docs/deploy-contract.md` (it runs the full gate itself and refuses a
     dirty tree). Green → `git add <your paths>` (never `-A`), `git commit`, `git push`, then
     check health from outside and read the logs of what restarted.
   - Any red gate (gate/deploy/health) → revert the slice (`git restore` /
     `git checkout --`), log the reason under "Done", skip the release. If a bad build already
     reached the server, use the project's rollback path (`docs/deploy-contract.md` §6).
7. **Sensitive zones — review only.** Auth, admin access, DB schema/migrations, security —
   **do not self-deploy** these. Found an improvement there → file it under "Needs review"
   in the backlog and continue with something safe.
8. **Report.** `./modules/bot/scripts/worker-bot.sh status <agent> "cycle N: <what was done>,
   <deployed/deferred>, next: <next item>"` if the worker-bot is wired up. Mark the item
   `[x]` in the backlog (move to "Done" with the date). Remove your row from `.agents/wip.md`.
9. **Continue.** If not stopped, make sure a recurring schedule exists for the next cycle
   (e.g. a ~25-30 min cron with the prompt "run one autopilot cycle per
   .claude/skills/base/autopilot/SKILL.md"), then end the turn. A new task from the queue
   arrives as a notification and interrupts the wait — handle it first.

## Guardrails (hard rules)

- **Money.** Zero spend on paid neural-net/AI APIs without explicit permission. Tests only
  use free paths.
- **Production.** Ship only fully green changes, only with a tree clean of foreign work. A
  failed health check must not be left live — roll back instead. Red gate = revert the slice.
- **Scope.** One small slice per cycle. No unrelated refactors. Sensitive zones go to review.
- **Git.** Only your own files, explicit paths. `git status` before every commit — never touch
  foreign changes.
- **Multi-agent.** Respect `.agents/wip.md`. Zone overlap → pick a different item. Deploy is
  exclusive.
- **Stop.** User says "stop autopilot" → cancel the recurring schedule, send a short
  confirmation. Also stop yourself after 3 empty cycles in a row (nothing to do) or 3 red
  cycles in a row (something is systemically broken — don't hammer prod, report and wait for
  a human).

## How this actually runs (the engine)

The skill is instructions; it does not run itself. The engine is **self-scheduling**:
- **Level 1 — while the session/IDE stays open (simple):** on `/автопилот`, create a
  recurring scheduled job (~25-30 min) with the prompt "run one autopilot cycle per this
  skill", and run the first cycle immediately. While the agent session is alive, cycles keep
  running unattended. A network drop breaks one tick; the next one resumes. The schedule is
  session-scoped — closing the session stops the engine.
- **Level 2 — fully unattended (survives closing/reboot):** an OS-level scheduler
  (cron / Task Scheduler) runs `modules/bot/scripts/keepalive.sh` every ~15 min (brings services back up
  after reboot/sleep) and triggers an autopilot cycle via a headless CLI run or by re-queuing
  a task to the bot. Needs one-time scheduler setup and explicit user consent (autostart +
  unmonitored token spend). Set this up only on direct request.

Always: work is cut into small slices, each committed, with a persistent backlog — after any
failure the next cycle picks up exactly where the last one left off, nothing lost.

## Sources of work

- **Production reliability** — recurring job errors from logs/redis. Highest value: users
  losing results.
- **Admin analytics** (if built) — funnel drop-off, abandoned flows, rage clicks. >50% drop
  at one step = a concrete UX item.
- **Code** — `TODO/FIXME/ponytail:` markers (see `tools/gather-signals.sh`).
- **User ideas** — fed in via the worker-bot queue, if wired up; go to the top of the backlog.

## Files

- `.agents/autopilot/backlog.md` — prioritized backlog + "Done" log.
- `tools/gather-signals.sh` — collect candidates from the code (TODO/FIXME/ponytail).
