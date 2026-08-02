# Bootstrap — turning this template into your project

You are starting a new project from this template. It carries **rules, workflow and agent
tooling** — no application code and no stack. Your job in this file: interview the user, fix the
stack, **stand up the verification loop**, and only then write the first feature.

Work through the steps in order. Step 4 is not optional and does not come later.

## 1. Interview (one short round)

Ask only what you cannot infer. Offer defaults, keep it to a handful of questions:

| Question | Why it matters |
|---|---|
| What are we building, in 1–2 sentences? | goes into `PROJECT.md`; every later decision refers back to it |
| Who uses it, and how do they reach it? | web / CLI / bot / desktop / library — decides the whole shape |
| Language and runtime? | if the user has no preference, recommend one and say why in a sentence |
| Does it store data? What kind? | picks the database, or rules one out |
| Where does it run when it's done? | their machine / a VPS / a cloud runtime / published as a package |
| Anything that must NOT change? | existing accounts, a chosen host, a required library |

Then ask for the MVP in one list: the smallest thing that is genuinely useful.

Do not offer an architecture menu. Pick the boring, well-supported option for their answers,
state the choice in one line with its trade-off, and move on.

## 2. Fill in the project's own context files

- **`PROJECT.md`** — what we are building, for whom, MVP scope, explicit non-goals.
- **`STACK.md`** — the chosen technologies, one row each, with versions. This is the file that
  answers "what do we use for X" for every later session.
- **`ARCH.md`** — the map: components, how a request/command flows end to end, where each kind of
  code lives. It starts small; it must never go stale.
- **`SESSION_HANDOFF.md`** — reset "Current state" to "fresh project, nothing shipped".

Keep `AGENTS.md`, `.claude/`, `.agents/`, `scripts/` as they are — those are the rules and the
tooling, and they are the reason this template exists.

## 3. Scaffold the smallest runnable skeleton

Not a feature — just enough that something runs and can be tested: entry point, dependency
manifest, one health/smoke path. No speculative structure, no folders "for later".

## 4. Stand up the gate — BEFORE the first feature

The rules in `AGENTS.md` say the gate is the only verdict before a release. Right now this
project has no gate, and `scripts/ci/test-gate.sh` refuses to run — deliberately.

1. Write `scripts/ci/zones/full.sh` for this stack (read `scripts/ci/zones/README.md`, copy
   `full.sh.example`). Add `backend.sh` / `frontend.sh` fast lanes only if the project is big
   enough to need them.
2. Write **one real test** — the smoke path from step 3. Not a placeholder that asserts `True`.
3. Run it:
   ```bash
   bash scripts/ci/test-gate.sh
   ```
   It must end with `gate green`.
4. Prove the gate can fail: break the code the test covers, rerun, confirm it goes red, restore.
   A gate nobody has seen fail is not known to work. If your tests run from a built image, the
   rebuild flag matters — otherwise you are testing the old code and reading it as "the test is
   empty".

Only when the gate is green AND has been seen red do you continue.

## 5. Deploy path (only if it ships somewhere)

If the project runs anywhere but the user's machine, create `scripts/ops/deploy.sh` following
`docs/deploy-contract.md`. If it does not deploy — a library, a CLI, a local tool — say so and
skip; the `выкати` command then means "publish/release" per that contract, or nothing at all.

## 6. First slice

Take the smallest useful item from the MVP list and ship it end to end under the normal rules:
plan first if it touches more than one file or 30 lines, test in the same change, narrow check,
then the full gate.

## 7. Clean up

- Delete this `init.md` and `UNIVERSAL-TEMPLATE-PLAN.md`.
- Remove `scripts/ci/zones/full.sh.example` once your real zones exist.
- Drop template parts the project will never use (Telegram worker-bot, proxy killswitch) rather
  than leaving dead scripts and docs lying around — dead tooling gets read as live and wastes
  the next session's time.
- Tell the user what was set up, what the gate covers, and what the first slice will be.
