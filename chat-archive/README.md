# Chat archive

Long-term copies of finished agent chats. Everything here except this file is gitignored —
transcripts stay local and are never shipped or committed.

Filled by the `запакуй` command (`.claude/commands/запакуй.md`): it gzips the session transcript
into `chat-<date>-<uuid8>.jsonl.gz`, appends a line to `INDEX.md`, and refreshes
`SESSION_HANDOFF.md`.

## Reading an archive

Do not load a transcript into context whole — they are large. Search instead:

```bash
zgrep -i "<what you are looking for>" chat-archive/*.jsonl.gz | head
zcat chat-archive/chat-2026-01-15-a1b2c3d4.jsonl.gz | jq -r 'select(.type=="user") | .message.content' | head -50
```

`INDEX.md` is the map: date, file, one or two lines about what the chat was about and what was
left open. Read it first and open only the archive that matters.

## Rules

- No secrets, tokens, PII or long logs in `INDEX.md`.
- A live session's transcript is also mirrored automatically to `.agents/sessions/` by the Stop
  hook — that is the working copy; this directory is the long-term one.
- When taking a transcript to archive, use YOUR OWN session id (from the scratchpad path), not the
  newest file in the directory: with a second agent working, the newest one is theirs.
