# Rule template

Copy one line into the matching section of `../SKILL.md`:

```
- <what to do, in the imperative or as a stated constraint> — <why, in one clause: what broke or
  what it costs otherwise> (<who decided>, <YYYY-MM-DD>).
```

Examples:

```
- Never show a spinner without a cancel path — a hung generation left users with no way out
  and they reloaded mid-charge (user, 2026-03-02).
- Free plan gets 3 projects, not a trial period — a time trial produced signups that never
  came back to convert (user, 2026-04-18).
- Emails go out from the queue, never inside the request — SMTP latency made registration
  look broken (2026-05-06).
```

Before adding, check the four tests in `../SKILL.md` → «How to add a rule»: durable, not
derivable from code, attributed, actionable.
