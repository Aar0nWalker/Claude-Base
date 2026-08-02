---
name: frontend-e2e
description: Use after UI edits to verify them in a real browser, and when a UI bug needs a regression test. Only relevant if the project has a browser interface.
---

# Browser verification (E2E)

Skip this skill entirely if the project has no browser UI.

## Run

```bash
GATE_ZONE=frontend bash scripts/ci/test-gate.sh   # the way the gate runs it
```

Locally, run your project's E2E command directly for a single spec, and repeat a suspicious one
in isolation before believing it is flaky.

## Rules

- **Mock every backend call.** Build the app under test against an unreachable backend on
  purpose, so a spec that forgets to mock fails loudly instead of silently depending on a live
  service. A test that reaches a real API will be slow, flaky, and eventually expensive.
- **Wait for a STATE, not for an element.** Markup that exists in several states proves nothing —
  waiting for a sidebar that renders for guests too will pass while login is broken. Expose the
  state in the DOM (`data-*` attribute) and wait for that. This is the number one cause of
  "flaky" UI tests, and it is the test lying about a working product.
- **Add a regression spec when fixing a real UI bug**, in the same change. Write it from the bug
  report *before* the fix: a test written afterwards tends to verify the fix rather than the bug.
- **Assert what the user sees**, not implementation detail. A test coupled to class names breaks
  on every restyle and teaches everyone to ignore it.
- Keep traces/screenshots of failures as artifacts, and read them before touching the product.

## Expected result

- the suite passes with no unmocked outbound request;
- the changed flow is covered, or you say explicitly why no spec was added.
