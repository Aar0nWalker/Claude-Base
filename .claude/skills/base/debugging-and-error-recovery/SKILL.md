---
name: debugging-and-error-recovery
description: Use when {{PROJECT_NAME}} has a failing build, broken deploy, production error, queue issue, or unexpected UI/API behavior — and always when the user reports a bug that feels familiar.
---

# Debugging And Error Recovery

Rule of this skill: **a bug the user reports a second time is fixed differently from the first.**
First time — the minimal edit. Second time — first a guard, then one shared place. Otherwise the
third report is guaranteed.

## Loop

```bash
python .claude/skills/base/debugging-and-error-recovery/tools/bug_ledger.py check <words about the bug>
```

0. **Ask the ledger, not yourself.** `check` shows the history of the zone straight from git plus
   recorded lessons. If there are >= 3 fixes — this is not a new bug: do not add one more special case.
1. Reproduce or locate the failing path.
2. Read the code that owns that path (not the neighbouring one).
3. Check logs and errors before guessing.
4. **Write the failing test first** — if the bug is a repeat or user-reported. A test written after
   the fix usually verifies the fix, not the bug.
5. Fix the shared root cause, not one visible symptom. Moving the trigger (one condition → another
   condition) is not a root cause.
6. Run the narrow check for the zone (`bash scripts/ci/check.sh <zone>`); if someone else's test
   fails, understand it instead of silencing it with a timeout.
7. **Record the lesson** — otherwise the skill does not learn and lies a month later:

```bash
python .claude/skills/base/debugging-and-error-recovery/tools/bug_ledger.py record \
  --area "login form" --symptom "what the user saw" \
  --cause "root cause, not the place you edited" --guard "<test that would fail before the fix>"
```

## A red test is not a flake until proven

Before calling a failure a flake:

- does it fail on **every retry in a row**, and on different commits? then it is a bug, not a race;
- does behaviour differ by zone (`GATE_ZONE=frontend` green, `full` red)? that is an environment
  difference, not proof of flakiness — first check what the test asserts about the product;
- if it really is a flake — fix the test's determinism, do not raise the timeout.

Skipping the gate (`SKIP_LOCAL_DOCKER_TESTS=1`) or narrowing it (`GATE_ZONE=`) happens only on the
user's direct request, and is named out loud in the report.

## Hotspots

_(Fill this in as the project teaches you where bugs cluster — the files you keep coming back to.
`bug_ledger.py hot` computes the candidates straight from git history. An empty list here after a
few months means nobody is looking.)_

- _(area: files)_

Monster files: do not read whole — `bash scripts/agents/codemap.sh <file>` for a symbol map, then
read only the range you need.

## What not to do

- Do not hide errors that should fail loudly in production.
- Do not close a repeat bug with a fix that has no guard — `record --guard no` says so honestly.
- Do not fix by the symptom in the report: find every caller of the shared place first.

## Weekly

```bash
python .claude/skills/base/debugging-and-error-recovery/tools/bug_ledger.py hot
```

Shows files with 3+ fixes in 60 days — those are places where the symptom gets fixed instead of the
cause. Each such zone needs either a lesson in the ledger or a task to dig in.
