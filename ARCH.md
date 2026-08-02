# Architecture — {{PROJECT_NAME}}

<!-- Filled during bootstrap (init.md) and kept current afterwards. This is the map a new
     session reads instead of scanning the repository. A stale map is worse than none: it sends
     the next session down a path that no longer exists. -->

## Flow

_(How a request / command / event travels end to end. A few lines of ASCII beat a paragraph.)_

```
_(user action) ──▶ _(entry point) ──▶ _(core logic) ──▶ _(storage / external service)
```

## Layer map

Where each kind of code lives, so nobody has to search for it.

| Layer | Path |
|---|---|
| Entry point | _(…)_ |
| Core logic | _(…)_ |
| Storage / data model | _(…)_ |
| External integrations | _(…)_ |
| Tests | _(…)_ |
| Gate zones | `scripts/ci/zones/` |

## Key modules

Only the ones worth knowing before touching anything. Not a directory listing.

| File | Responsibility |
|---|---|
| _(…)_ | _(…)_ |

## Gotchas

Things that cost someone real time. Add one whenever you get bitten; delete one when it stops
being true. This section is the highest-value part of this file.

- _(the surprising behaviour, and what to do about it)_

## Verification

- Full gate: `bash scripts/ci/test-gate.sh` — see [docs/test-gate.md](docs/test-gate.md).
- What each zone covers: _(one line per zone)_
- What is deliberately NOT covered by automated tests, and why: _(…)_
