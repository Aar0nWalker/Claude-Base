---
name: planning-and-task-breakdown
description: Use for splitting {{PROJECT_NAME}} development work into small agent-ready tasks, especially when sub-agents can work in parallel or when a change touches multiple files.
---

# Planning And Task Breakdown

Use this before non-trivial implementation.

Keep the plan short:

1. Name the user-visible goal.
2. Identify the smallest affected areas.
3. Split work into independent tasks only when they have disjoint files or responsibilities.
4. Give sub-agents tasks only when they can produce a useful result without owning final integration.
5. Keep deploy, production checks, and git operations in the main agent.

For each task, define:

- owner: main agent or sub-agent;
- files/modules;
- expected output;
- verification.

Stop planning once the next safe edit is clear.
