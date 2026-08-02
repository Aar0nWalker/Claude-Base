#!/usr/bin/env python3
"""Bug ledger: what has already been fixed here, why it came back, what guards it now.

The point is one thing: don't fix the symptom of something that has been fixed three times
already. Before a fix, `check` shows the history of the zone straight from git (nobody
maintains it by hand, so it cannot go stale) plus recorded lessons; after a fix, `record`
stores the lesson "symptom -> cause -> guard".

  check <words>   what was already fixed in this zone -- BEFORE you edit
  record ...      lesson after a fix (mandatory if the bug is a repeat)
  hot             zones that get fixed again and again (pure git distillation)
  list            recorded lessons
  selfcheck       verify this script

The ledger stores NO derived data: repeat clusters are recomputed from git every time.
Only the lessons, which git does not contain, are stored.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path

LEDGER = Path(__file__).with_name("bugs.json")
REPO = Path(__file__).resolve().parents[5]
# ponytail: "repeatedly fixed zone" = >=REPEAT_MIN fix commits touching one file. A rough
# heuristic, but computed from what is written anyway. If real issue numbers ever appear,
# cluster by those instead.
REPEAT_MIN = 3
SCAN_DAYS = 60
# Files that change in every commit for any reason: always on top, say nothing about bugs.
NOISE = re.compile(r"^(docs/|\.agents/|chat-archive/|.*\.md$|.*/__pycache__/)")


def _git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return out.stdout if out.returncode == 0 else ""


def _load() -> dict:
    if not LEDGER.exists():
        return {"records": []}
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    data.setdefault("records", [])
    return data


def _save(data: dict) -> None:
    LEDGER.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fix_commits(days: int = SCAN_DAYS) -> list[tuple[str, str, str, list[str]]]:
    """(hash, date, subject, files) for fix commits in the last `days`."""
    raw = _git(
        "log", f"--since={days}.days", "--no-merges", "--name-only",
        "--pretty=format:%x01%h%x09%ad%x09%s", "--date=short",
    )
    out: list[tuple[str, str, str, list[str]]] = []
    for block in raw.split("\x01"):
        block = block.strip("\n")
        if not block:
            continue
        head, _, rest = block.partition("\n")
        parts = head.split("\t")
        if len(parts) < 3:
            continue
        sha, when, subject = parts[0], parts[1], parts[2]
        if not re.match(r"^(fix|hotfix|revert|ui)[(:]", subject, re.I):
            continue
        files = [f for f in rest.splitlines() if f and not NOISE.match(f)]
        out.append((sha, when, subject, files))
    return out


def hot_zones(days: int = SCAN_DAYS, limit: int = 15) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for _sha, _when, _subject, files in fix_commits(days):
        counter.update(set(files))
    return [(f, n) for f, n in counter.most_common(limit) if n >= REPEAT_MIN]


def _match(text: str, words: list[str]) -> bool:
    low = text.lower()
    return all(w.lower() in low for w in words)


def cmd_check(args, data: dict) -> None:
    words = args.words
    print(f"# already fixed, by words: {' '.join(words)}\n")

    hits = [(s, w, subj, files) for s, w, subj, files in fix_commits(args.days)
            if _match(subj, words) or any(_match(f, words) for f in files)]
    if hits:
        print(f"## fixes in {args.days} days: {len(hits)}")
        for sha, when, subject, _files in hits[:12]:
            print(f"  {when}  {sha}  {subject}")
        if len(hits) >= 3:
            print(f"\n  !! fixed {len(hits)} times — this is NOT a new bug. Look for the one shared")
            print("     place instead of adding another special case. The symptom just moved.")
    else:
        print(f"## no fixes in {args.days} days — probably a new bug")

    lessons = [r for r in data["records"]
               if _match(" ".join(str(v) for v in r.values()), words)]
    if lessons:
        print(f"\n## recorded lessons: {len(lessons)}")
        for r in lessons:
            print(f"  [{r.get('date')}] {r.get('area')}")
            print(f"    symptom: {r.get('symptom')}")
            print(f"    cause:   {r.get('cause')}")
            print(f"    guard:   {r.get('guard')}")

    guards = [r.get("guard", "") for r in lessons if r.get("guard") and r["guard"] != "no"]
    print("\n## what to do")
    if guards:
        print("  1. Run the existing guard BEFORE editing — it must fail:")
        for g in sorted(set(guards)):
            print(f"       {g}")
    else:
        print("  1. No guard exists. Write the test that fails on the current bug, then fix.")
    print("  2. After the fix: bug_ledger.py record --area ... --symptom ... --cause ... --guard ...")


def cmd_hot(args, data: dict) -> None:
    zones = hot_zones(args.days, args.limit)
    print(f"# zones with >={REPEAT_MIN} fixes in {args.days} days (candidates for 'fixing the symptom')\n")
    if not zones:
        print("  clean")
        return
    covered = {r.get("area", "") for r in data["records"]}
    for path, n in zones:
        mark = "" if any(path in c or c in path for c in covered if c) else "   <- no lesson recorded"
        print(f"  {n:>2} fixes  {path}{mark}")


def cmd_record(args, data: dict) -> None:
    rec = {
        "date": args.date or date.today().isoformat(),
        "area": args.area,
        "symptom": args.symptom,
        "cause": args.cause,
        "guard": args.guard,
    }
    if args.commits:
        rec["commits"] = args.commits
    if args.note:
        rec["note"] = args.note
    data["records"].append(rec)
    _save(data)
    print(f"recorded: {rec['area']} -> guard {rec['guard']}")
    if args.guard.strip().lower() in {"no", "none", "-", ""}:
        print("!! a fix without a guard — this bug will come back. Add a test before closing.")


def cmd_list(args, data: dict) -> None:
    rows = data["records"]
    if args.area:
        rows = [r for r in rows if args.area.lower() in str(r.get("area", "")).lower()]
    print(f"# lessons: {len(rows)}")
    for r in rows:
        print(f"\n[{r.get('date')}] {r.get('area')}")
        print(f"  symptom: {r.get('symptom')}")
        print(f"  cause:   {r.get('cause')}")
        print(f"  guard:   {r.get('guard')}")
        if r.get("commits"):
            print(f"  commits: {r['commits']}")


def cmd_selfcheck(args, data: dict) -> None:
    assert NOISE.match("docs/plans/x.md") and NOISE.match("ARCH.md"), "noise not filtered"
    assert not NOISE.match("backend/app/worker.py"), "code mistaken for noise"
    assert _match("Login form regression", ["login"]), "search does not find substrings"
    assert not _match("login", ["login", "admin"]), "search must require ALL words"
    assert LEDGER.exists(), "bugs.json missing"
    assert isinstance(_load()["records"], list), "records is not a list"
    commits = fix_commits(30)
    assert all(len(c) == 4 for c in commits), "git log parsing broken"
    assert not any(f.endswith(".md") for _s, _w, _t, files in commits for f in files), "noise in files"
    print(f"selfcheck ok (fix commits in 30 days: {len(commits)}, lessons: {len(data['records'])})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check", help="what was already fixed in this zone")
    p.add_argument("words", nargs="+")
    p.add_argument("--days", type=int, default=SCAN_DAYS)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("hot", help="zones fixed again and again")
    p.add_argument("--days", type=int, default=SCAN_DAYS)
    p.add_argument("--limit", type=int, default=15)
    p.set_defaults(fn=cmd_hot)

    p = sub.add_parser("record", help="lesson after a fix")
    p.add_argument("--area", required=True, help="zone: file/screen/behaviour")
    p.add_argument("--symptom", required=True, help="what the user saw")
    p.add_argument("--cause", required=True, help="root cause, not the place you edited")
    p.add_argument("--guard", required=True, help="test that would fail before the fix, or 'no'")
    p.add_argument("--commits", default="")
    p.add_argument("--note", default="")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_record)

    p = sub.add_parser("list", help="recorded lessons")
    p.add_argument("--area", default="")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("selfcheck")
    p.set_defaults(fn=cmd_selfcheck)

    args = ap.parse_args()
    args.fn(args, _load())


if __name__ == "__main__":
    main()
