# Stack

<!-- Filled during bootstrap (init.md), then kept current. This file answers "what do we use
     for X" so no session has to re-derive it or guess. One row per choice, with a version. -->

Chosen technologies for {{PROJECT_NAME}}. Use these when adding a module unless a task says
otherwise. Adding a NEW dependency is a decision — record it here in the same change.

| Module / concern | Technology | Version |
|---|---|---|
| Language / runtime | _(…)_ | _(…)_ |
| Package manager | _(…)_ | _(…)_ |
| Storage / database | _(or "none")_ | _(…)_ |
| Test runner | _(…)_ | _(…)_ |
| Static check / linter | _(…)_ | _(…)_ |
| Build / packaging | _(…)_ | _(…)_ |
| Runtime target | _(where it runs in production)_ | _(…)_ |

## Rules

- Don't hardcode technology or model names — read them from env / constants.
- Secrets only from environment or secret storage, never in code or logs.
- Never expose PII (phones, emails, tokens) in responses or logs.
- Raw user input only through parameterized queries / escaped commands.
- Prefer the boring, well-supported option. A dependency is a permanent liability: before adding
  one, check whether the standard library or something already installed covers it.
