# The test gate

There is no external CI. **The local gate is the only verdict** before anything is released.

```bash
bash scripts/ci/test-gate.sh                 # full gate — what a release runs
bash scripts/ci/check.sh backend             # narrow zone for a routine turn
```

The verdict is the line `gate green` in the output — **not** the exit code of whatever you ran it
through. A pipe through `tail` returns `tail`'s status, and `docker wait` returns 0 for a run that
was killed from outside. Both have shipped broken code by being believed.

## Two halves

| Half | Where | Who writes it |
|---|---|---|
| Runner — guards, timeout, logs, verdict | `scripts/ci/test-gate.sh` | this template, unchanged |
| Zones — what actually runs | `scripts/ci/zones/*.sh` | the project, at bootstrap |

A missing `zones/full.sh` is a hard error. A gate that passes because nothing ran is worse than
no gate: it manufactures confidence. See `scripts/ci/zones/README.md` for the zone contract.

## What the runner guarantees

- **A hung run dies.** `GATE_TIMEOUT` (default 1500s) kills the zone instead of waiting forever.
  Nobody may be watching, and a stuck gate never un-sticks itself. Raising the timeout is the
  last resort, after finding what it waited on.
- **Full logs survive.** Everything lands in `.gate-logs/<zone>.log` — a 120-line tail is never
  enough to diagnose a real failure, and cleanup takes container logs with it.
- **Cheap guards run first**, before anything slow:
  - `test-lifecycle-check.sh` — behaviour changed but no test did → red. Escape hatch is a
    `no-test: <reason>` line in the commit message, so a bypass leaves a trace. It also rejects
    tests disabled without a stated reason (`@pytest.mark.skip`, `test.skip`, `t.Skip`,
    `#[ignore]`).
  - CRLF guard — a `.sh` with Windows line endings does not parse in bash, and the failure it
    produces points at something unrelated.

## When it fails

1. Read `.gate-logs/<zone>.log` — the full output, not the tail on screen.
2. **A red test is not a flake until proven.** Rerun it in isolation, repeatedly. If every first
   attempt fails, it is a stable bug that retries were hiding. If it truly is non-deterministic,
   fix the test's determinism — never raise the timeout to make it pass.
3. Suspect the test before the product when it waits for an *element* to appear rather than a
   *state* to hold. That is the single most common cause of "flaky" UI tests.
4. Fix the cause and rerun in the same task. Do not hand back a known regression.

## Keeping it honest

- **Run the full gate on a cooled-down machine.** Right after parallel agent runs it produces
  false timeouts: the run swells several times over and failures land on timeouts rather than
  assertions. That is overload, not code.
- **Verify a test by breaking the code it covers**, at least once, when you write it. If your
  tests run from a built image, the code is usually COPIED in at build time — rebuild, or you are
  testing the old code and will read "still green" as "the test is empty".
- **Never delete, weaken or skip a test to get to green.** A test failing after your edit did
  its job.
- **Never let the gate call a paid API.** Not once, not "just to check".

## Parallel runs

Two working trees would tear down each other's containers. Namespace anything global by
`TEST_GATE_PROJECT_NAME`; `scripts/agents/worktree.sh new <name>` sets it up for you.
