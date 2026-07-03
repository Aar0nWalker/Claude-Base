---
name: code-review-and-quality
description: Use before deploy/push, after sub-agent changes, or when reviewing {{PROJECT_NAME}} diffs for bugs, regressions, missing verification, and unnecessary complexity.
---

# Code Review And Quality

Review order:

1. Behavioral bugs.
2. Security/auth risks.
3. Broken API or schema contracts.
4. Missing migrations or caller updates.
5. UI regressions and text/layout issues.
6. Unnecessary complexity.

For sub-agent work:

- review changed files before integration;
- do not trust generated code without checking local patterns;
- main agent owns final tests, deploy, and git.

Before reporting done:

- run the smallest practical verification;
- mention any skipped check;
- keep the final summary short.
