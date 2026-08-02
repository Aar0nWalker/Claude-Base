---
name: incremental-implementation
description: Use for implementing {{PROJECT_NAME}} changes in small verified slices without broad refactors or speculative abstractions.
---

# Incremental Implementation

Default flow:

1. Read nearby files first.
2. Make the smallest useful change.
3. Update every caller when changing a contract.
4. Verify imports/types for the touched code.
5. Avoid unrelated formatting and refactors.
6. Commit only the requested files.

Prefer one vertical slice that works end to end over a large rewrite that works nowhere yet.

## What a small diff hides

- **A second copy of the truth.** Constants duplicated across layers (limits, prices, tiers,
  feature flags, status names) drift silently and the bug surfaces months later. Either derive one
  from the other, or add a check that fails when they disagree.
- **Persisted shape.** A schema or file-format change ships with its migration in the same change,
  and that migration must be safe to run twice. Expand → migrate → contract, never a one-shot edit.
- **Background work.** Changing what a job does means checking the whole path: what enqueues it,
  what happens on retry, and what happens if it dies halfway through.
- **User-facing surfaces.** Don't change behaviour outside the requested path. When a UI moves,
  check the states nobody demos: empty, loading, error, and far too much data.

## When to stop and plan instead

More than one file or 30 lines, or you cannot name the check that proves it works — write the
short plan first (AGENTS.md → Rules). The check is part of the design, not follow-up work.
