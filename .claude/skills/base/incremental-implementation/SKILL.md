---
name: incremental-implementation
description: Use for implementing {{PROJECT_NAME}} changes in small verified slices without broad refactors or speculative abstractions.
---

# Incremental Implementation

Default flow:

1. Read nearby files first.
2. Make the smallest useful change.
3. Update every caller when changing a contract.
4. Verify imports/types for touched code.
5. Avoid unrelated formatting and refactors.
6. Commit only the requested files.

Prefer one vertical slice over a large rewrite.

For frontend:

- preserve existing state shape and API helpers;
- avoid changing UX outside the requested path;
- check text overflow and mobile layout when UI changes.

For backend:

- keep schema changes paired with an idempotent startup migration in `db.py`;
- keep any cross-tier constants (limits, plan tiers, feature flags) aligned between frontend and backend;
- avoid background worker (ARQ) behavior changes without checking the queue flow end to end.
