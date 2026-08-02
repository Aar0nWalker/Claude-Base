# Gate zones — the project-specific half of the gate

`scripts/ci/test-gate.sh` is stack-agnostic. **What actually runs is here**, one script per zone.
Written once at bootstrap, before the first feature — the feedback loop is part of the design,
not follow-up work.

```
zones/full.sh       everything. REQUIRED — a deploy always runs this zone.
zones/backend.sh    optional fast lane for server-side changes
zones/frontend.sh   optional fast lane for UI changes
```

Missing `full.sh` is a hard error, not a silent pass: a gate that goes green because nothing ran
manufactures false confidence, which is worse than having no gate.

## Contract for a zone script

1. **Exit non-zero when anything fails.** That is the whole interface. Use `set -euo pipefail`
   and never end a pipeline with something that swallows the status (`| tail`, `| tee` without
   `PIPESTATUS`).
2. **Hermetic.** No production database, no real credentials, no paid API, ideally no network.
   Disposable services, blank keys, throwaway data. A test that reaches a live external service
   will be flaky and will eventually cost money.
3. **Free.** Never call a paid AI/media API from the gate. That rule has no exceptions the agent
   can grant itself.
4. **Self-cleaning.** Whatever you start (containers, temp dirs), remove on exit — including on
   failure. Use `trap cleanup EXIT INT TERM`.
5. **Loud about where it broke.** Print the failing test's name and enough context to act on.
   The runner keeps your full output in `.gate-logs/<zone>.log`.
6. **Finite.** Assume the runner will kill you at `GATE_TIMEOUT`. Don't wait on anything forever.

## Examples

`full.sh.example` is a working shape — copy it and replace the commands with your stack's.

Rough sizing from a real project: unit tests ~1 min, the full gate 5–8 min. If your full zone
grows past ~10 minutes, split a fast lane out rather than letting everyone skip the gate.

## Running in parallel

Two working trees must not tear down each other's containers. Namespace anything global by
`TEST_GATE_PROJECT_NAME` (e.g. `docker compose --project-name "$TEST_GATE_PROJECT_NAME"`).
`scripts/agents/worktree.sh` sets that variable for you.
