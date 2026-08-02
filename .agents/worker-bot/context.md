# Worker Bot Compact Context

Auto-generated append-only log, written by `scripts/worker_bot.py` (`append_compact_context`).
Every task/status/question/answer event across all agents gets one line here, trimmed to the
last ~40 events. An agent picking up a task reads this file instead of re-scanning the whole
project to work out what is going on.

Do not hand-edit the event log below this header — the bot's `trim_markdown_events` keeps
non-`- ` lines (like this header) and drops old `- ` event lines once the cap is hit. This file
is gitignored (runtime state, may contain user-specific context); this copy only exists as a
template so a fresh checkout has the file present with an explanatory header instead of a bot
crash on missing file.

## Log
