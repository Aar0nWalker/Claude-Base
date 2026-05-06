# [Project Name] — Architecture

## Mission

<!-- TODO: 1-2 sentences. What does this product do? Who uses it? -->

## Stack

<!-- Fill as modules are added. Defaults for each module are in STACK.md.
- Backend: ...
- Frontend: ...
- Infra: ...
-->

## Layer Map

<!-- Fill as modules are added. -->
| Layer | Path |
|-------|------|
| <!-- TODO --> | `<!-- TODO -->` |

<!-- TODO: key architectural rules, e.g.:
- Business logic in services/, not routers
- Never return ORM objects from API — use schemas
-->

## Key Modules

<!-- Non-obvious files and what they exclusively own. -->
| File | Responsibility |
|------|---------------|
| `TODO` | TODO |

## Data Model

<!-- TODO: core entities, non-obvious fields, constraints, state machines.
- Entity — key fields, invariants
- Entity — status: A → B → C
-->

## Runtime Constraints

<!-- Project-specific only. Universal rules (async, secrets, etc.) are in STACK.md.
- Redis TTLs: X codes Ns, Y cache Ns
- SELECT FOR UPDATE on: [resources requiring locks]
- [other project-specific constraints]
-->

## Known Gotchas

<!-- Non-obvious bugs and correct patterns discovered during development.
Add here to avoid re-discovering in future sessions.
- **Thing**: what goes wrong and the correct fix/pattern
-->

## Testing

<!-- TODO: fill when test suite is set up.
Run all:      e.g. docker compose run --rm api python -m pytest tests/ -x --tb=short
Run one file: e.g. docker compose run --rm api python -m pytest tests/test_foo.py -x
Fixtures/factories: ...
Known flakiness: ...
-->
