---
name: learned-rules
description: Use before product, UX, copy, pricing or generation-logic decisions in {{PROJECT_NAME}} — the accumulated project rules of what works, what broke, and why. Also use to record a new rule after the user corrects a decision.
---

# {{PROJECT_NAME}} Learned Rules

The rules a fresh session cannot derive from the code: decisions the user already made, things
tried and rejected, and non-obvious product behaviour. Code and git history are NOT duplicated here.

**Read before**: product/UX decisions, copy, pricing, prompts, anything the user has opinions about.
**Write after**: the user corrects a decision, or a choice turns out wrong in production.

## Rules

<!-- Start empty. Add rules as the project teaches them — see «How to add» below. -->

### Product

- _(none yet)_

### UX / copy

- _(none yet)_

### Technical decisions

- _(none yet)_

## How to add a rule

Copy `tools/rule-template.md`, fill it in, append it to the right section above. A rule earns its
place only if it passes all four:

1. **Durable** — it will still be true next month. Today's bug is not a rule; the lesson from it is.
2. **Not derivable** — it is not visible in the code, the tests, or git history. If a reader could
   find it by reading the file, do not write it down.
3. **Attributed** — who decided, and when (`(user, YYYY-MM-DD)`). An unattributed rule cannot be
   revisited later.
4. **Actionable** — it tells the next session what to DO, not what happened.

Bad: "Fixed the button on the pricing page."
Good: "Prices are shown per month, never per year with an asterisk — the year view read as a
discount and generated refund requests (user, 2026-03-14)."

## Retire rules too

A rule that has been overtaken (the feature changed, the user changed their mind) gets DELETED, not
annotated. A stale rule is worse than a missing one: the next session will follow it confidently.
When the user contradicts a rule here, update this file in the same turn.

Bug lessons (symptom → cause → guard) belong in the bug ledger instead:
`.claude/skills/base/debugging-and-error-recovery/tools/bug_ledger.py`.
