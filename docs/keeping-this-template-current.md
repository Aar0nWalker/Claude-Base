# Keeping this template current

This template is meant to be updated continuously from real projects. Every rule in `AGENTS.md`
exists because something went wrong once — that is the only reason a rule earns its place here.

## What belongs here

A finding is worth promoting into the template when all four hold:

1. **It generalizes.** True for a bot, a game, a CLI and a web service alike. Anything that names
   a framework belongs in that project's `ARCH.md`, not here.
2. **It cost something.** A wasted hour, a bad deploy, a silently skipped test, a wrong answer
   shipped confidently. Preferences without a cost are noise.
3. **It changes behaviour.** The next session does something different because of it. A rule
   nobody can act on is decoration.
4. **It is not already covered.** Adding a fifth phrasing of an existing rule makes the file
   longer and each rule weaker.

## Where it goes

| Finding | Home |
|---|---|
| How the agent should work | `AGENTS.md` — keep it short, it loads every session |
| Repeatable procedure | a skill in `.claude/skills/base/` (with a `tools/` script if it repeats) |
| Something a script can enforce | `scripts/ci/` — a guard beats a paragraph nobody rereads |
| Claude-only behaviour | `.claude/CLAUDE.md` or a command in `.claude/commands/` |
| A property releases must have | `docs/deploy-contract.md` |
| A property the gate must have | `docs/test-gate.md` + the runner |

**Prefer a guard over a rule.** A sentence in a document is obeyed while someone remembers it; a
check in the gate is obeyed always. Several rules here started as prose and became scripts —
the CRLF guard and the "a test is part of the change" guard both did.

## Harvesting from a live project

At the end of a project — or whenever something bites twice — ask:

- What did I have to explain to the agent more than once? → a rule or a skill.
- What went red in a way the gate should have caught earlier? → a new guard or zone.
- Which lesson lives in that project's bug ledger and would apply anywhere? → promote it.
- What in here turned out to be **wrong** or no longer true? → delete it. A stale rule is worse
  than a missing one, because it gets followed confidently.

Copy the wording almost verbatim from where it was learned, keeping the concrete example that
made it obvious — a rule with its scar tissue attached is far easier to apply than an abstraction.

## Reviewing the size

Hot files (`AGENTS.md`, `.claude/CLAUDE.md`) are loaded in full, every session. Growth is not
free: at some point every added line makes the others less likely to be followed. When `AGENTS.md`
starts feeling long, do not summarize it — delete the rules that no longer earn their place, and
move the detailed ones behind a skill that is loaded on demand.
