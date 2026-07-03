#!/usr/bin/env python3
"""Send a worker-bot task to Codex.

The debug CLI starts a fresh thread. This helper first tries the app-server
protocol path that can resume an existing project thread, then falls back to the
debug CLI before the task is lost.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import select
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".agents" / "worker-bot"
THREAD_ID_FILE = STATE_DIR / "codex-thread-id"
SESSIONS_DIR = Path.home() / ".codex" / "sessions"
APP_SERVER_SOCK = Path.home() / ".codex" / "app-server-control" / "app-server-control.sock"


class AppServerError(RuntimeError):
    pass


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


def first_session_meta(path: Path) -> dict[str, Any] | None:
    try:
        line = path.open("r", encoding="utf-8", errors="ignore").readline()
        item = json.loads(line)
    except (OSError, json.JSONDecodeError):
        return None
    if item.get("type") != "session_meta":
        return None
    payload = item.get("payload")
    return payload if isinstance(payload, dict) else None


def find_current_thread_id() -> str | None:
    for key in ("WORKER_CODEX_THREAD_ID", "CODEX_THREAD_ID"):
        env_id = os.environ.get(key, "").strip()
        if env_id:
            return env_id

    if THREAD_ID_FILE.exists():
        file_id = THREAD_ID_FILE.read_text(encoding="utf-8", errors="ignore").strip()
        if file_id:
            return file_id

    if not SESSIONS_DIR.exists():
        return None

    root = normalize_path(str(ROOT))
    candidates: list[tuple[int, int, float, str]] = []
    for path in SESSIONS_DIR.rglob("rollout-*.jsonl"):
        meta = first_session_meta(path)
        if not meta:
            continue
        if normalize_path(str(meta.get("cwd") or "")) != root:
            continue
        if meta.get("thread_source") == "subagent" or meta.get("agent_role"):
            continue
        thread_id = str(meta.get("session_id") or meta.get("id") or "").strip()
        if not thread_id:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        # Prefer the main user thread; use size/mtime to avoid tiny debug threads.
        user_rank = 1 if meta.get("thread_source") == "user" else 0
        candidates.append((user_rank, stat.st_size, stat.st_mtime, thread_id))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][3]


def find_session_file(thread_id: str) -> Path | None:
    if not SESSIONS_DIR.exists():
        return None
    matches = list(SESSIONS_DIR.rglob(f"rollout-*{thread_id}.jsonl"))
    if matches:
        return max(matches, key=lambda item: item.stat().st_mtime)
    for path in SESSIONS_DIR.rglob("rollout-*.jsonl"):
        meta = first_session_meta(path)
        if meta and str(meta.get("session_id") or meta.get("id") or "") == thread_id:
            return path
    return None


def compact_text(value: str, limit: int = 500) -> str:
    value = " ".join(value.split())
    if not value or value.startswith("<<ccr:"):
        return ""
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."


def recent_chat_context(thread_id: str, limit: int = 16) -> str:
    path = find_session_file(thread_id)
    if not path:
        return f"Current Codex thread id: {thread_id}"

    items: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return f"Current Codex thread id: {thread_id}"

    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        if item.get("type") == "event_msg" and payload.get("type") == "agent_message":
            text = compact_text(str(payload.get("message") or ""))
            if text:
                items.append(f"assistant: {text}")
            continue
        if item.get("type") != "response_item":
            continue
        if payload.get("type") != "message":
            continue
        role = payload.get("role")
        if role not in {"user", "assistant"}:
            continue
        chunks: list[str] = []
        content = payload.get("content")
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = compact_text(str(part.get("text") or ""))
                if text:
                    chunks.append(text)
        text = compact_text(" ".join(chunks), 900)
        if text:
            items.append(f"{role}: {text}")

    if not items:
        return f"Current Codex thread id: {thread_id}\nSession file: {path}"

    return "\n".join(
        [
            f"Current Codex thread id: {thread_id}",
            f"Session file: {path}",
            "Recent current-chat context:",
            *items[-limit:],
        ]
    )


def with_fallback_context(message: str, thread_id: str | None) -> str:
    if not thread_id:
        return message
    return f"{message}\n\n<current_chat_context>\n{recent_chat_context(thread_id)}\n</current_chat_context>"


def send_json(proc: subprocess.Popen[str], method: str, params: dict[str, Any] | None = None, request_id: str | None = None) -> None:
    payload: dict[str, Any] = {"method": method}
    if request_id is not None:
        payload["id"] = request_id
    if params is not None:
        payload["params"] = params
    if proc.stdin is None:
        raise AppServerError("app-server stdin unavailable")
    proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
    proc.stdin.flush()


def read_json(proc: subprocess.Popen[str], timeout: float) -> dict[str, Any]:
    if proc.stdout is None:
        raise AppServerError("app-server stdout unavailable")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([proc.stdout], [], [], max(0.1, min(1.0, deadline - time.monotonic())))
        if not ready:
            if proc.poll() is not None:
                raise AppServerError(f"app-server exited {proc.returncode}")
            continue
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                raise AppServerError(f"app-server exited {proc.returncode}")
            time.sleep(0.05)
            continue
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            print(line, file=sys.stderr)
    raise AppServerError("timeout waiting for app-server")


def wait_response(proc: subprocess.Popen[str], request_id: str, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = read_json(proc, max(0.1, deadline - time.monotonic()))
        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise AppServerError(json.dumps(message["error"], ensure_ascii=False))
        result = message.get("result")
        return result if isinstance(result, dict) else {}
    raise AppServerError(f"timeout waiting for {request_id}")


def wait_turn_completed(proc: subprocess.Popen[str], thread_id: str, turn_id: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = read_json(proc, max(0.1, deadline - time.monotonic()))
        if message.get("method") != "turn/completed":
            continue
        params = message.get("params")
        if not isinstance(params, dict) or params.get("threadId") != thread_id:
            continue
        turn = params.get("turn")
        if not isinstance(turn, dict) or turn.get("id") != turn_id:
            continue
        if turn.get("error"):
            raise AppServerError(json.dumps(turn["error"], ensure_ascii=False))
        return
    raise AppServerError(f"timeout waiting for turn {turn_id}")


def protocol_command(use_proxy: bool) -> list[str]:
    if use_proxy:
        command = ["codex", "app-server", "proxy"]
        if APP_SERVER_SOCK.exists():
            command.extend(["--sock", str(APP_SERVER_SOCK)])
        return command
    return ["codex", "app-server", "--stdio"]


def protocol_send(message: str, thread_id: str, timeout: float, use_proxy: bool, wait_complete: bool = False) -> None:
    proc = subprocess.Popen(
        protocol_command(use_proxy),
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        init_id = str(uuid.uuid4())
        send_json(
            proc,
            "initialize",
            {
                "clientInfo": {
                    "name": "{{PROJECT_SLUG}}-worker-dispatcher",
                    "title": "{{PROJECT_NAME}} Worker Dispatcher",
                    "version": "1",
                },
                "capabilities": {
                    "experimentalApi": True,
                    "requestAttestation": False,
                    "optOutNotificationMethods": [
                        "command/exec/outputDelta",
                        "item/agentMessage/delta",
                        "item/plan/delta",
                        "item/fileChange/outputDelta",
                        "item/reasoning/summaryTextDelta",
                        "item/reasoning/textDelta",
                    ],
                },
            },
            init_id,
        )
        wait_response(proc, init_id, 20)
        send_json(proc, "initialized")

        resume_id = str(uuid.uuid4())
        send_json(proc, "thread/resume", {"threadId": thread_id, "cwd": str(ROOT)}, resume_id)
        wait_response(proc, resume_id, 40)

        turn_request_id = str(uuid.uuid4())
        send_json(
            proc,
            "turn/start",
            {
                "threadId": thread_id,
                "clientUserMessageId": None,
                "input": [{"type": "text", "text": message, "text_elements": []}],
                "cwd": str(ROOT),
            },
            turn_request_id,
        )
        result = wait_response(proc, turn_request_id, 40)
        turn = result.get("turn")
        turn_id = turn.get("id") if isinstance(turn, dict) else None
        if not isinstance(turn_id, str) or not turn_id:
            raise AppServerError("turn/start did not return turn id")
        if wait_complete:
            wait_turn_completed(proc, thread_id, turn_id, timeout)
    finally:
        with contextlib.suppress(Exception):
            proc.terminate()
            proc.wait(timeout=5)


def debug_fallback(message: str, timeout: float) -> None:
    subprocess.run(
        ["codex", "debug", "app-server", "send-message-v2", message],
        cwd=str(ROOT),
        check=True,
        timeout=timeout,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message")
    parser.add_argument("--thread-id", default="auto")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("WORKER_CODEX_TURN_TIMEOUT_SECONDS", "1800")))
    parser.add_argument("--wait-complete", action="store_true")
    parser.add_argument("--print-target", action="store_true")
    args = parser.parse_args()

    thread_id = find_current_thread_id() if args.thread_id == "auto" else args.thread_id.strip()
    if args.print_target:
        print(thread_id or "")
        return 0 if thread_id else 1

    if thread_id:
        modes = (True, False) if args.wait_complete else (True,)
        for use_proxy in modes:
            try:
                protocol_send(args.message, thread_id, args.timeout, use_proxy, args.wait_complete)
                return 0
            except AppServerError as exc:
                mode = "proxy" if use_proxy else "stdio"
                print(f"codex app-server {mode} failed: {exc}", file=sys.stderr)
                require_headroom = os.environ.get("WORKER_CODEX_REQUIRE_HEADROOM", "1").strip().lower()
                if use_proxy and require_headroom not in {"0", "false", "no"}:
                    print(
                        "not falling back to codex debug because WORKER_CODEX_REQUIRE_HEADROOM is enabled",
                        file=sys.stderr,
                    )
                    return 2

    print("falling back to codex debug app-server send-message-v2", file=sys.stderr)
    debug_fallback(with_fallback_context(args.message, thread_id), args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
