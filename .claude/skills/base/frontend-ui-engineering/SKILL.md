---
name: frontend-ui-engineering
description: Use for {{PROJECT_NAME}} user interface work — layout, states, copy, visual QA, screenshots. Only relevant if the project has a user interface.
---

# UI Engineering

Skip this skill if the project has no user interface.

## Rules

- Match the patterns already in the project before inventing new ones: find the existing component
  primitives and design tokens and reuse them. A second styling approach is a permanent tax.
- **Cover every state, not just the happy one:** loading, empty, error, and "far more data than the
  designer imagined". Missing states are the most common UI bug and they never appear in a demo.
- Any modal or overlay stays closable — ✕, backdrop click and Esc — no matter what is loading
  behind it. A user trapped in a dialog will reload the page and lose their work.
- Keep copy plain and aimed at someone who does not know how the system works inside. Never
  mention features, tiers or payments the product does not actually support yet.
- Keep controls predictable: tabs for modes, toggles for binary choices, inputs for numbers.
- Don't resize or restyle things nobody asked about.
- Check both a narrow and a wide screen for overlap, overflow and alignment.
- State that must survive a multi-step flow (wizard, onboarding) lives in one place — not
  re-derived at each step, where the steps inevitably disagree.

## Verifying

Reading the code does not tell you what the screen looks like. When visual correctness matters,
take a screenshot before declaring it done: `tools/screenshot.py` (configure the URLs and, if the
page needs a session, the login details via env). For flows rather than single screens, write a
browser test instead — see the `frontend-e2e` skill.
