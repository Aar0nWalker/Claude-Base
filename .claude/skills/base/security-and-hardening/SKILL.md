---
name: security-and-hardening
description: Use for auth, cookies, admin routes, external API keys, user uploads, webhooks, and production-facing integrations in {{PROJECT_NAME}}.
---

# Security And Hardening

Security defaults:

- secrets only from environment variables;
- no tokens, emails, passwords, or API keys in logs;
- auth checks on every protected endpoint;
- admin checks on every admin endpoint;
- ORM or parameterized queries only;
- validate external URLs and uploaded files;
- keep cookie auth httpOnly/Secure/SameSite where applicable;
- use `credentials: 'include'` for cookie-backed frontend calls.

For mutations:

- preserve Origin/CSRF checks;
- avoid trusting frontend-only state;
- enforce any credit/quota/rate limits server-side only;
- make retries idempotent when jobs or paid external calls are involved.

Before deploy, verify the protected path still fails closed.
