---
name: frontend-ui-engineering
description: Use for {{PROJECT_NAME}} frontend, landing, app shell, admin UI, responsive layout, copy, visual QA, and screenshots. This project skill has priority over generic frontend guidance.
---

# Frontend UI Engineering

This project skill is the first frontend reference for {{PROJECT_NAME}} UI work.

Rules:

- match existing UI patterns before inventing new ones (`components/ui/*`, `app/globals.css` design tokens);
- keep copy simple for non-technical users;
- do not mention features, tiers, or payments the product doesn't currently support;
- avoid marketing fluff in operational (app) screens;
- keep controls predictable: tabs for modes, toggles for binary choices, inputs/sliders for numbers;
- use compact layouts for app screens and richer visuals only on the landing page;
- check mobile and desktop for overlap, overflow, and alignment.

Conventions:

- `providers.tsx` composes toast + confirm + auth context — reuse it, don't add ad-hoc providers;
- admin-only or experimental features stay gated behind the admin check until enabled for everyone;
- any state that must persist across a multi-step flow (wizard, onboarding) should live in one place, not be re-derived per step.

When visual correctness matters, use screenshots before finalizing: `tools/screenshot.py`.
