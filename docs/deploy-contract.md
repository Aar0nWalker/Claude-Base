# Deploy contract

This template ships no deploy script — where a project runs is a property of that project.
It ships the **properties a deploy must have**, learned from a production system where each one
was paid for with an incident.

If the project deploys anywhere, create `scripts/ops/deploy.sh` satisfying everything below.
If it does not deploy (a library, a CLI, a local tool), say so in `ARCH.md` and skip this file;
the `выкати` command then means "release/publish" or nothing at all.

## Required properties

1. **Runs the full gate first, and stops on red.**
   A red gate is a reason to stop, not a hurdle to route around. Skipping must be impossible
   without a written reason (`SKIP_REASON='…'`), and the skip must be shouted in the output.
   An agent never grants itself that skip — only the user, in the same message.

2. **Refuses a dirty working tree.**
   If the deploy ships the working copy (rsync, `docker build .`, a file sync) rather than a
   committed revision, a dirty tree silently ships whatever is lying around — including another
   agent's half-finished work. Check `git status --porcelain` (untracked files count: they get
   shipped too). Override only via an explicit variable that states a reason, and mark the
   release SHA `-dirty` when used.

3. **Refuses an unexpected branch.** Same reasoning, cheaper to check.

4. **Logs the whole run to a file from the first second.**
   A deploy takes minutes. Whoever is watching must be able to `tail -f` progress instead of
   blocking on the command. Write `deploy.run.log` from line one, not a summary at the end.

5. **Never hides its exit status behind a pipe.**
   `cmd | tail` returns `tail`'s status. Print an unambiguous final line and treat THAT as the
   verdict, the same way the gate does with `gate green`.

6. **Has a way back.** A rollback path (previous image, previous release directory, a tag) that
   is tested at least once. "We'll rebuild from git" is not a rollback plan during an outage.

7. **Checks health after, from outside.**
   Hit the public entry point and read the logs of what you just restarted. If the deploy is
   blue/green or otherwise keeps the old process alive, make sure you are querying the NEW one —
   asking the old slot returns a healthy answer about the code you just replaced.

8. **Carries no secrets.** Everything sensitive comes from the environment or the server; never
   from the repository, the log, or the chat.

## Batching

The deploy is an expensive tail (build + transfer + warm-up). Ship several edits from one
request in ONE deploy at the end rather than one per edit. Risky changes — auth, payments,
schema — get their own deploy so a rollback does not drag everything else with it.

## Schema and data

Changes to a schema go expand → migrate → contract, in separate releases: add the new shape
(old code ignores it), deploy, switch the code over, deploy, and only then remove the old shape
once no running version reads it. Stop reading first, drop later — never in the same release.
