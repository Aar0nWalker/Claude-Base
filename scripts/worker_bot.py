#!/usr/bin/env python3
"""Local Telegram bot for Claude/Codex task coordination.

Runtime state is intentionally kept under .agents/worker-bot/ (gitignored).
The bot token is read from WORKER_BOT_TOKEN or local .env without printing it.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = Path(os.environ.get("WORKER_BOT_STATE_DIR") or ROOT / ".agents" / "worker-bot")
STATE_FILE = STATE_DIR / "state.json"
INBOX_FILE = STATE_DIR / "inbox.md"
SCREEN_REQUEST_FILE = STATE_DIR / "screen_request.json"
LOCK_FILE = STATE_DIR / ".lock"
CURRENT_PREFIX = "current"
AGENT_CHATS_DIR = STATE_DIR / "agents"
COMPACT_CONTEXT_FILE = STATE_DIR / "context.md"
MAX_CHAT_EVENTS = 80
MAX_CONTEXT_EVENTS = 40
TERMINAL_TASK_STATUSES = {"done", "cancelled"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_dotenv_value(key: str) -> str:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return ""
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def bot_token() -> str:
    return os.environ.get("WORKER_BOT_TOKEN", "").strip() or load_dotenv_value("WORKER_BOT_TOKEN")


def google_api_key() -> str:
    return os.environ.get("GOOGLE_API_KEY", "").strip() or load_dotenv_value("GOOGLE_API_KEY")


def allowed_user_ids() -> set[str]:
    raw = os.environ.get("WORKER_BOT_ALLOWED_USER_IDS", "").strip() or load_dotenv_value("WORKER_BOT_ALLOWED_USER_IDS")
    return {item.strip() for item in raw.split(",") if item.strip()}


def default_state() -> dict[str, Any]:
    return {
        "owner_chat_id": os.environ.get("WORKER_BOT_ALLOWED_CHAT_ID", "").strip(),
        "last_update_id": 0,
        "next_task_id": 1,
        "next_question_id": 1,
        "tasks": [],
        "questions": [],
        "chat_modes": {},
        "agent_status": {},
        "events": [],
    }


@contextlib.contextmanager
def state_lock():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("a+", encoding="utf-8") as lock:
        try:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        except Exception:
            pass
        try:
            yield
        finally:
            try:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return default_state()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = default_state()
    base = default_state()
    base.update(data if isinstance(data, dict) else {})
    return base


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATE_FILE)
    render_inbox(state)


def add_event(state: dict[str, Any], text: str) -> None:
    events = state.setdefault("events", [])
    events.append({"at": utc_now(), "text": text})
    del events[:-80]


def current_task_file(agent: str) -> Path:
    safe_agent = "".join(ch for ch in agent.strip() if ch.isalnum() or ch in {"-", "_"}) or "Agent"
    return STATE_DIR / f"{CURRENT_PREFIX}-{safe_agent}.md"


def compact_line(value: str, limit: int = 900) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def safe_agent_key(agent: str | None) -> str:
    value = str(agent or "agent").strip().lower()
    return "".join(ch for ch in value if ch.isalnum() or ch in {"-", "_"}) or "agent"


def agent_chat_file(agent: str | None) -> Path:
    return AGENT_CHATS_DIR / safe_agent_key(agent) / "chat.md"


def append_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def trim_markdown_events(path: Path, keep: int) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    event_indexes = [idx for idx, line in enumerate(text) if line.startswith("- ")]
    if len(event_indexes) <= keep:
        return
    cutoff = event_indexes[-keep]
    kept_header = [line for line in text[:cutoff] if not line.startswith("- ")]
    path.write_text("\n".join(kept_header + text[cutoff:]).rstrip() + "\n", encoding="utf-8")


def append_agent_chat(agent: str | None, actor: str, text: str) -> None:
    path = agent_chat_file(agent)
    if not path.exists():
        append_lines(
            path,
            [
                f"# Telegram Agent Chat: {agent_title(agent)}",
                "",
                f"Agent: {safe_agent_key(agent)}",
                f"Created: {utc_now()}",
                "",
                "## Chat And Tasks",
            ],
        )
    append_lines(path, [f"- {utc_now()} {actor}: {compact_line(text)}"])
    trim_markdown_events(path, MAX_CHAT_EVENTS)


def append_task_chat(task: dict[str, Any] | None, actor: str, text: str) -> None:
    if not task:
        return
    agent = task.get("claimed_by") or task.get("owner") or "agent"
    append_agent_chat(str(agent), actor, text)


def append_compact_context(actor: str, text: str) -> None:
    append_lines(COMPACT_CONTEXT_FILE, [f"- {utc_now()} {actor}: {compact_line(text, 700)}"])
    trim_markdown_events(COMPACT_CONTEXT_FILE, MAX_CONTEXT_EVENTS)


def format_task_context(task: dict[str, Any], agent: str) -> str:
    chat_path = agent_chat_file(agent)
    return (
        f"# Telegram Worker Bot Task\n\n"
        f"Agent: {agent}\n"
        f"Task: #{task.get('id')}\n"
        f"Owner: {task.get('owner', 'claude')}\n\n"
        f"{task.get('text', '')}\n\n"
        f"Agent chat: `{chat_path}`\n"
        f"Compact bot context: `{COMPACT_CONTEXT_FILE}`\n\n"
        f"When finished, run: `./scripts/worker-bot.sh done {task.get('id')}`\n"
    )


def write_current_task(agent: str, task: dict[str, Any]) -> str:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    text = format_task_context(task, agent)
    current_task_file(agent).write_text(text, encoding="utf-8")
    return text


def read_current_task(agent: str) -> str:
    path = current_task_file(agent)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def clear_current_task(task_id: int) -> None:
    if not STATE_DIR.exists():
        return
    needle = f"Task: #{task_id}"
    for path in STATE_DIR.glob(f"{CURRENT_PREFIX}-*.md"):
        try:
            if needle in path.read_text(encoding="utf-8", errors="ignore"):
                path.unlink()
        except OSError:
            pass


def render_inbox(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    open_tasks = [t for t in state.get("tasks", []) if t.get("status") not in TERMINAL_TASK_STATUSES]
    pending_questions = [q for q in state.get("questions", []) if q.get("status") == "pending"]
    lines = [
        "# Worker Bot Inbox",
        "",
        f"Updated: {utc_now()}",
        "",
        "## Agent Status",
    ]
    statuses = state.get("agent_status", {})
    if statuses:
        for name, item in sorted(statuses.items()):
            lines.append(f"- **{name}** ({item.get('at', 'unknown')}): {item.get('text', '')}")
    else:
        lines.append("- No status yet.")
    lines += ["", "## Open Tasks"]
    if open_tasks:
        for task in open_tasks:
            owner = task.get("owner") or "claude"
            lines.append(f"- #{task.get('id')} [{owner}] {task.get('text')} ({task.get('status')})")
    else:
        lines.append("- No open tasks.")
    lines += ["", "## Pending Questions"]
    if pending_questions:
        for question in pending_questions:
            lines.append(f"- Q{question.get('id')} from {question.get('agent')}: {question.get('text')}")
    else:
        lines.append("- No pending questions.")
    lines += ["", "## Recent Events"]
    for event in state.get("events", [])[-20:]:
        lines.append(f"- {event.get('at')}: {event.get('text')}")
    INBOX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


class Telegram:
    def __init__(self, token: str):
        self.token = token
        self.base = f"https://api.telegram.org/bot{token}"

    def call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(f"{self.base}/{method}", data=body)
        with urllib.request.urlopen(req, timeout=70) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data}")
        return data

    def send(
        self,
        chat_id: str | int,
        text: str,
        *,
        keyboard: bool = True,
        html_mode: bool = False,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"chat_id": str(chat_id), "text": text[:3900]}
        if html_mode:
            payload["parse_mode"] = "HTML"
        if reply_markup is not None:
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        elif keyboard:
            payload["reply_markup"] = json.dumps(MAIN_KEYBOARD, ensure_ascii=False)
        return self.call("sendMessage", payload)

    def send_chat_action(self, chat_id: str | int, action: str = "typing") -> None:
        self.call("sendChatAction", {"chat_id": str(chat_id), "action": action})

    def send_photo(self, chat_id: str | int, photo_path: str, caption: str = "") -> dict[str, Any]:
        """Upload a local image via multipart sendPhoto (stdlib only, no requests)."""
        import mimetypes
        import uuid

        with open(photo_path, "rb") as f:
            content = f.read()
        fname = os.path.basename(photo_path)
        ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
        boundary = uuid.uuid4().hex
        parts: list[bytes] = []
        for name, value in (("chat_id", str(chat_id)), ("caption", caption[:1024])):
            if value:
                parts.append(
                    f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
                )
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="{fname}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n".encode() + content + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        req = urllib.request.Request(
            f"{self.base}/sendPhoto",
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data}")
        return data

    def answer_callback(self, callback_query_id: str, text: str = "", *, show_alert: bool = False) -> None:
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text[:200]
        if show_alert:
            payload["show_alert"] = "true"
        self.call("answerCallbackQuery", payload)

    def edit_message(
        self,
        chat_id: str | int,
        message_id: int | str,
        text: str,
        *,
        html_mode: bool = False,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        """Edit in place; True on success or no-op ("message is not modified")."""
        payload = {"chat_id": str(chat_id), "message_id": str(message_id), "text": text[:3900]}
        if html_mode:
            payload["parse_mode"] = "HTML"
        if reply_markup is not None:
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        try:
            self.call("editMessageText", payload)
            return True
        except Exception as exc:
            return "message is not modified" in str(exc)

    def edit_reply_markup(self, chat_id: str | int, message_id: int | str, reply_markup: dict[str, Any] | None = None) -> None:
        payload = {
            "chat_id": str(chat_id),
            "message_id": str(message_id),
            "reply_markup": json.dumps(reply_markup or {"inline_keyboard": []}, ensure_ascii=False),
        }
        try:
            self.call("editMessageReplyMarkup", payload)
        except Exception:
            pass

    def pin_message(self, chat_id: str | int, message_id: int | str) -> None:
        try:
            self.call("pinChatMessage", {"chat_id": str(chat_id), "message_id": str(message_id), "disable_notification": "true"})
        except Exception:
            pass

    def updates(self, offset: int) -> list[dict[str, Any]]:
        timeout = os.environ.get("WORKER_BOT_POLL_TIMEOUT_SECONDS", "4").strip() or "4"
        data = self.call("getUpdates", {"offset": str(offset), "timeout": timeout})
        return data.get("result") or []

    def me(self) -> dict[str, Any]:
        return self.call("getMe", {}).get("result") or {}

    def file_path(self, file_id: str) -> str:
        result = self.call("getFile", {"file_id": file_id}).get("result") or {}
        file_path = str(result.get("file_path") or "")
        if not file_path:
            raise RuntimeError("Telegram did not return file_path")
        return file_path

    def download_file(self, file_path: str) -> bytes:
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        with urllib.request.urlopen(url, timeout=90) as resp:
            return resp.read()


def owner_allowed(state: dict[str, Any], chat_id: int) -> bool:
    owner = str(state.get("owner_chat_id") or "").strip()
    return bool(owner) and owner == str(chat_id)


def user_allowed(user_id: int | None) -> bool:
    allowed = allowed_user_ids()
    return not allowed or (user_id is not None and str(user_id) in allowed)


def claim_owner_if_empty(state: dict[str, Any], chat_id: int) -> bool:
    if str(state.get("owner_chat_id") or "").strip():
        return False
    state["owner_chat_id"] = str(chat_id)
    add_event(state, f"Owner chat claimed: {chat_id}")
    save_state(state)
    return True


def send_working_heartbeat(tg: Telegram, state: dict[str, Any]) -> None:
    owner_chat_id = str(state.get("owner_chat_id") or "").strip()
    if not owner_chat_id:
        return
    active = any(task.get("status") == "claimed" for task in state.get("tasks", []))
    if not active:
        return
    now = time.time()
    last = float(state.get("last_heartbeat_at") or 0)
    if now - last < 4:
        return
    try:
        tg.send_chat_action(owner_chat_id, "typing")
        state["last_heartbeat_at"] = now
        save_state(state)
    except Exception:
        pass


def parse_owner(text: str) -> tuple[str, str]:
    value = text.strip()
    if value.startswith("[") and "]" in value:
        owner, rest = value[1:].split("]", 1)
        return owner.strip().lower() or "claude", rest.strip()
    return "claude", value


def transcribe_voice(tg: Telegram, file_id: str) -> str:
    key = google_api_key()
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set")

    file_path = tg.file_path(file_id)
    audio = tg.download_file(file_path)
    model = os.environ.get("WORKER_BOT_TRANSCRIBE_MODEL", "gemini-2.5-flash").strip()
    base_url = os.environ.get("WORKER_BOT_GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com").rstrip("/")
    url = f"{base_url}/v1beta/models/{model}:generateContent?key={urllib.parse.quote(key)}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Расшифруй голосовое сообщение на русском языке. "
                            "Верни только текст задачи, без комментариев и кавычек."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "audio/ogg",
                            "data": base64.b64encode(audio).decode("ascii"),
                        }
                    },
                ]
            }
        ]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    text = " ".join(str(part.get("text") or "").strip() for part in parts).strip()
    if not text:
        raise RuntimeError("empty transcription")
    return text


def add_task(state: dict[str, Any], text: str) -> dict[str, Any]:
    owner, task_text = parse_owner(text)
    task = {
        "id": state["next_task_id"],
        "text": task_text,
        "owner": owner,
        "status": "open",
        "created_at": utc_now(),
    }
    state["next_task_id"] += 1
    state.setdefault("tasks", []).append(task)
    add_event(state, f"Task #{task['id']} added for {owner}")
    append_task_chat(task, "user", task_text)
    append_compact_context("user", f"Task #{task['id']} for {owner}: {task_text}")
    save_state(state)
    return task


def mark_done(state: dict[str, Any], task_id: int) -> bool:
    for task in state.get("tasks", []):
        if task.get("id") == task_id:
            task["status"] = "done"
            task["done_at"] = utc_now()
            clear_current_task(task_id)
            add_event(state, f"Task #{task_id} done")
            append_task_chat(task, "system", "Task closed")
            append_compact_context("system", f"Task #{task_id} closed")
            save_state(state)
            return True
    return False


def cancel_task(state: dict[str, Any], task_id: int, actor: str = "user") -> bool:
    for task in state.get("tasks", []):
        if task.get("id") == task_id and task.get("status") not in TERMINAL_TASK_STATUSES:
            task["status"] = "cancelled"
            task["cancelled_at"] = utc_now()
            task["cancelled_by"] = actor
            clear_current_task(task_id)
            add_event(state, f"Task #{task_id} cancelled by {actor}")
            append_task_chat(task, "system", f"Task cancelled by {actor}")
            append_compact_context("system", f"Task #{task_id} cancelled by {actor}")
            save_state(state)
            return True
    return False


def release_task(state: dict[str, Any], task_id: int, reason: str = "") -> bool:
    for task in state.get("tasks", []):
        if task.get("id") == task_id and task.get("status") == "claimed":
            agent = str(task.get("claimed_by") or task.get("owner") or "agent")
            task["status"] = "open"
            task["released_at"] = utc_now()
            if reason:
                task["release_reason"] = reason
            clear_current_task(task_id)
            add_event(state, f"Task #{task_id} released")
            append_task_chat(task, "system", f"Task released: {reason or 'dispatch failed'}")
            append_compact_context("system", f"Task #{task_id} released: {reason or 'dispatch failed'}")
            set_status(state, agent, f"Задача #{task_id} вернулась в очередь: {reason or 'ошибка отправки'}")
            save_state(state)
            return True
    return False


def claim_next_task(state: dict[str, Any], agent: str) -> dict[str, Any] | None:
    agent_key = agent.strip().lower()
    candidates = [t for t in state.get("tasks", []) if t.get("status") == "open"]
    candidates.sort(key=lambda t: not bool(t.get("priority")))  # priority first, stable
    for task in candidates:
        owner = str(task.get("owner") or "claude").lower()
        if owner in {agent_key, "both", "any"}:
            task["status"] = "claimed"
            task["claimed_by"] = agent
            task["claimed_at"] = utc_now()
            add_event(state, f"Task #{task['id']} claimed by {agent}")
            append_task_chat(task, agent, "Task claimed")
            append_compact_context(agent, f"Task #{task['id']} claimed")
            save_state(state)
            return task
    return None


def hook_context(state: dict[str, Any], agent: str) -> str:
    current = read_current_task(agent)
    if current:
        return current
    task = claim_next_task(state, agent)
    if not task:
        return ""
    return write_current_task(agent, task)


def active_task_for_agent(state: dict[str, Any], agent: str) -> dict[str, Any] | None:
    agent_key = agent.strip().lower()
    for task in reversed(state.get("tasks", [])):
        owner = str(task.get("owner") or "claude").lower()
        claimed_by = str(task.get("claimed_by") or "").lower()
        if task.get("status") == "claimed" and (owner == agent_key or claimed_by == agent_key):
            return task
    return None


def add_question(state: dict[str, Any], agent: str, text: str, options: list[str] | None = None) -> dict[str, Any]:
    task = active_task_for_agent(state, agent)
    question = {
        "id": state["next_question_id"],
        "agent": agent,
        "text": text,
        "status": "pending",
        "created_at": utc_now(),
    }
    if options:
        question["options"] = options
    if task:
        question["task_id"] = task.get("id")
        question["task_text"] = task.get("text")
    state["next_question_id"] += 1
    state.setdefault("questions", []).append(question)
    add_event(state, f"Question Q{question['id']} from {agent}")
    if task:
        append_task_chat(task, agent, f"Question Q{question['id']}: {text}")
    else:
        append_agent_chat(agent, agent, f"Question Q{question['id']}: {text}")
    append_compact_context(agent, f"Question Q{question['id']}: {text}")
    save_state(state)
    return question


def answer_question(state: dict[str, Any], qid: int, text: str) -> bool:
    for question in state.get("questions", []):
        if question.get("id") == qid:
            question["status"] = "answered"
            question["answer"] = text
            question["answered_at"] = utc_now()
            add_answer_followup_task(state, question, text)
            add_event(state, f"Question Q{qid} answered")
            task = task_by_id(state, int(question.get("task_id") or 0)) if question.get("task_id") else None
            if task:
                append_task_chat(task, "user", f"Answer Q{qid}: {text}")
            else:
                append_agent_chat(question.get("agent"), "user", f"Answer Q{qid}: {text}")
            append_compact_context("user", f"Answer Q{qid}: {text}")
            save_state(state)
            return True
    return False


def add_answer_followup_task(state: dict[str, Any], question: dict[str, Any], answer: str) -> dict[str, Any]:
    agent = str(question.get("agent") or "codex").strip() or "codex"
    task_id = question.get("task_id")
    prefix = f"Ответ на вопрос Q{question.get('id')}"
    if task_id:
        prefix += f" по задаче #{task_id}"
    task_text = (
        f"{prefix}:\n{answer}\n\n"
        "Продолжи работу с учётом ответа пользователя."
    )
    task = add_task(state, f"[{agent}] {task_text}")
    task["source_question_id"] = question.get("id")
    if task_id:
        task["parent_task_id"] = task_id
    add_event(state, f"Follow-up task #{task['id']} added from Q{question.get('id')}")
    append_task_chat(task, "system", f"Follow-up from Q{question.get('id')}")
    return task


def agent_title(agent: str | None) -> str:
    value = str(agent or "Codex").strip().lower()
    if value == "codex":
        return "Codex -- Bob"
    if value == "claude":
        return "Claude -- Lead"
    return str(agent or "Agent").strip() or "Agent"


def task_notice(agent: str | None, task_id: int | str | None, status: str, response: str, *, ok: bool = True) -> str:
    header = f"<b>{html.escape(agent_title(agent))}</b>"
    if task_id is not None:
        header += f" · задача #{html.escape(str(task_id))}"
    icon = "✅" if ok else "❌"
    return (
        f"{header}\n\n"
        f"{icon} {html.escape(status)}\n\n"
        f"Ответ от агента:\n{html.escape(response.strip() or '-')}"
    )


def question_notice(agent: str | None, question_id: int | str, text: str, options: list[str] | None = None) -> str:
    body = (
        f"<b>{html.escape(agent_title(agent))}</b> Вопрос Q{html.escape(str(question_id))}\n"
        f"Когда: {html.escape(utc_now())}\n\n"
        f"❓ Нужен ответ\n\n"
        f"Вопрос от агента:\n{html.escape(text.strip() or '-')}"
    )
    # Buttons truncate long option text, so spell the full variants out in the message
    # body and number them — the button number maps to the line the user reads here.
    if options:
        body += "\n\nВарианты:\n" + "\n".join(
            f"{i + 1}. {html.escape(opt)}" for i, opt in enumerate(options)
        )
    return body


def task_id_from_text(text: str) -> str | None:
    match = re.search(r"#(\d+)", text)
    return match.group(1) if match else None


def task_by_id(state: dict[str, Any], task_id: int) -> dict[str, Any] | None:
    for task in state.get("tasks", []):
        if task.get("id") == task_id:
            return task
    return None


def mark_notified(state: dict[str, Any], task: dict[str, Any]) -> None:
    task["notified_at"] = utc_now()
    save_state(state)


def set_status(state: dict[str, Any], agent: str, text: str) -> None:
    state.setdefault("agent_status", {})[agent] = {"text": text, "at": utc_now()}
    add_event(state, f"{agent} status: {text}")
    task_id = task_id_from_text(text)
    task = task_by_id(state, int(task_id)) if task_id else active_task_for_agent(state, agent)
    if task:
        append_task_chat(task, agent, f"Status: {text}")
    else:
        append_agent_chat(agent, agent, f"Status: {text}")
    append_compact_context(agent, f"Status: {text}")
    save_state(state)


def summary(state: dict[str, Any]) -> str:
    # High-level only: counts + what each agent is doing right now. Task/queue detail
    # lives behind the «Очередь» button (queue_card_text) so this stays glanceable.
    active_tasks = [t for t in state.get("tasks", []) if t.get("status") == "claimed"]
    queued_tasks = [t for t in state.get("tasks", []) if t.get("status") == "open"]
    pending_questions = [q for q in state.get("questions", []) if q.get("status") == "pending"]
    lines = [
        "📊 Статус",
        f"🟢 В работе: {len(active_tasks)} · ⏳ В очереди: {len(queued_tasks)} · ❓ Вопросов: {len(pending_questions)}",
    ]
    statuses = state.get("agent_status", {})
    if statuses:
        lines.append("")
        for name, item in sorted(statuses.items()):
            txt = str(item.get("text") or "").split("\n", 1)[0]
            txt = txt[:90] + ("…" if len(txt) > 90 else "")
            lines.append(f"• {name}: {txt}" if txt else f"• {name}: —")
    lines.append("")
    lines.append("📋 Детали задач — кнопка «Очередь».")
    return "\n".join(lines)


def queue_text(state: dict[str, Any]) -> str:
    open_tasks = [t for t in state.get("tasks", []) if t.get("status") not in TERMINAL_TASK_STATUSES]
    if not open_tasks:
        return "Открытых задач нет."
    return "\n".join(
        f"#{t['id']} [{t.get('owner', 'claude')}] {t.get('status', 'open')}: {t.get('text')}"
        for t in open_tasks[:30]
    )


def task_actions_keyboard(task_id: int | str) -> dict[str, Any]:
    return {
        "inline_keyboard": [[
            {"text": "Отменить", "callback_data": f"cancel_task:{task_id}"},
            {"text": "Приоритет", "callback_data": f"prio_task:{task_id}"},
            {"text": "Уточнить", "callback_data": f"clarify_task:{task_id}"},
        ]]
    }


def queue_card_text(state: dict[str, Any]) -> str:
    def short(item: dict[str, Any], key: str = "text") -> str:
        txt = str(item.get(key) or "").split("\n", 1)[0]
        return txt[:80] + ("…" if len(txt) > 80 else "")

    active = [t for t in state.get("tasks", []) if t.get("status") == "claimed"]
    waiting = [t for t in state.get("tasks", []) if t.get("status") == "open"]
    pending_q = [q for q in state.get("questions", []) if q.get("status") == "pending"]
    lines = ["📌 Очередь"]
    lines.append("")
    lines.append("В работе:" + ("" if active else " нет"))
    lines.extend(f"⚙️ #{t['id']} [{t.get('claimed_by') or t.get('owner', 'claude')}] {short(t)}" for t in active[:8])
    lines.append("Ожидают:" + ("" if waiting else " нет"))
    lines.extend(f"{'❗' if t.get('priority') else '•'} #{t['id']} [{t.get('owner', 'claude')}] {short(t)}" for t in waiting[:12])
    if pending_q:
        lines.append("Вопросы без ответа:")
        lines.extend(f"❓ Q{q['id']} {q.get('agent')}: {short(q)}" for q in pending_q[:6])
    return "\n".join(lines)


def notify_queue_empty(tg: Telegram, state: dict[str, Any], prev_active: int | None, now_active: int) -> None:
    """Short ping when the last task finishes (transition >0 -> 0 within this run)."""
    if prev_active is None or prev_active == 0 or now_active > 0:
        return
    owner = str(state.get("owner_chat_id") or "").strip()
    if not owner:
        return
    try:
        tg.send(owner, "Все задачи выполнены, очередь пустая. Можно закидывать следующие.")
    except Exception:
        pass


def count_active_tasks(state: dict[str, Any]) -> int:
    return sum(1 for t in state.get("tasks", []) if t.get("status") in {"open", "claimed"})


def refresh_queue_card(tg: Telegram, state: dict[str, Any]) -> None:
    """Edit one pinned queue message instead of sending new ones. Only the run
    loop calls this (under state_lock), so parallel CLI writers never race the edit."""
    owner = str(state.get("owner_chat_id") or "").strip()
    if not owner:
        return
    text = queue_card_text(state)
    if text == state.get("queue_card_text"):
        return
    msg_id = state.get("queue_card_message_id")
    if msg_id and tg.edit_message(owner, msg_id, text):
        state["queue_card_text"] = text
        save_state(state)
        return
    try:
        resp = tg.send(owner, text, keyboard=False)
        new_id = (resp.get("result") or {}).get("message_id")
        if new_id:
            state["queue_card_message_id"] = new_id
            tg.pin_message(owner, new_id)
        state["queue_card_text"] = text
        save_state(state)
    except Exception:
        pass


def task_cancel_keyboard(state: dict[str, Any]) -> dict[str, Any] | None:
    tasks = [t for t in state.get("tasks", []) if t.get("status") not in TERMINAL_TASK_STATUSES]
    if not tasks:
        return None
    return {
        "inline_keyboard": [
            [{"text": f"Отменить #{task['id']}", "callback_data": f"cancel_task:{task['id']}"}] for task in tasks[:20]
        ]
    }


def questions_text(state: dict[str, Any]) -> str:
    pending = [q for q in state.get("questions", []) if q.get("status") == "pending"]
    if not pending:
        return "Вопросов нет."
    return "\n".join(f"Q{q['id']} {q.get('agent')}: {q.get('text')}" for q in pending[:30])


def question_id_from_reply(message: dict[str, Any]) -> int | None:
    reply = message.get("reply_to_message") or {}
    source = " ".join(str(reply.get(key) or "") for key in ("text", "caption"))
    match = re.search(r"\bQ(\d+)\b", source)
    return int(match.group(1)) if match else None


def dispatch_open_tasks(tg: Telegram, state: dict[str, Any]) -> None:
    owner_chat_id = str(state.get("owner_chat_id") or "").strip()
    if not owner_chat_id:
        return
    for task in state.get("tasks", []):
        if task.get("status") != "open" or task.get("notified_at"):
            continue
        task["notified_at"] = utc_now()
        tg.send(
            owner_chat_id,
            task_notice(task.get("owner", "claude"), task.get("id"), "Задачу принял", "Агент начнёт работу, когда дойдёт очередь."),
            html_mode=True,
            reply_markup=task_actions_keyboard(task["id"]),
        )


MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "+ Claude"}, {"text": "+ Codex"}],
        [{"text": "Статус"}, {"text": "Очередь"}],
        [{"text": "Скрин VS Code"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

HELP = """Кнопки:
+ Claude — отправить задачу Claude
+ Codex — отправить задачу Codex
Статус — коротко: счётчики и чем заняты агенты сейчас
Очередь — задачи в работе и в очереди с тем, что ты просил, компактно
Скрин VS Code — скриншот VS Code с рабочего компа (нужен запущенный вотчер)

На вопрос агента нажми Ответить в Telegram и отправь текст.
"""


def chat_key(chat_id: int) -> str:
    return str(chat_id)


def get_mode(state: dict[str, Any], chat_id: int) -> dict[str, Any]:
    modes = state.setdefault("chat_modes", {})
    item = modes.get(chat_key(chat_id))
    return item if isinstance(item, dict) else {}


def set_mode(state: dict[str, Any], chat_id: int, mode: str, **data: Any) -> None:
    state.setdefault("chat_modes", {})[chat_key(chat_id)] = {"mode": mode, "data": data, "at": utc_now()}
    save_state(state)


def clear_mode(state: dict[str, Any], chat_id: int) -> None:
    state.setdefault("chat_modes", {}).pop(chat_key(chat_id), None)
    save_state(state)


def handle_button(tg: Telegram, state: dict[str, Any], chat_id: int, text: str) -> bool:
    if text in {"+ Claude", "Задачи", "➕ Задача"}:
        set_mode(state, chat_id, "awaiting_task", owner="claude")
        tg.send(chat_id, "Напиши задачу для Claude.")
        return True
    if text in {"+ Codex", "➕ Задача Codex"}:
        set_mode(state, chat_id, "awaiting_task", owner="codex")
        tg.send(chat_id, "Напиши текст задачи для Codex.")
        return True
    if text in {"Скрин VS Code", "Скрин экрана"}:  # legacy label kept so cached keyboards still map to VS Code, not a new task
        target = "vscode"
        SCREEN_REQUEST_FILE.write_text(
            json.dumps({"target": target, "requested_at": utc_now()}, ensure_ascii=False),
            encoding="utf-8",
        )
        tg.send(chat_id, "Запросил скрин — прилетит сюда через несколько секунд (если вотчер на компе запущен).")
        return True
    if text in {"Очередь", "📋 Очередь"}:
        clear_mode(state, chat_id)
        tg.send(chat_id, queue_card_text(state), reply_markup=task_cancel_keyboard(state))
        return True
    if text in {"Статус", "📊 Статус"}:
        clear_mode(state, chat_id)
        tg.send(chat_id, summary(state), reply_markup=task_cancel_keyboard(state))
        return True
    if text == "❓ Вопросы":
        pending = [q for q in state.get("questions", []) if q.get("status") == "pending"]
        if not pending:
            clear_mode(state, chat_id)
            tg.send(chat_id, "Вопросов нет.")
            return True
        set_mode(state, chat_id, "awaiting_answer")
        tg.send(chat_id, questions_text(state) + "\n\nНапиши ответ. Если вопросов несколько: номер и текст ответа.")
        return True
    if text == "✅ Закрыть":
        open_tasks = [t for t in state.get("tasks", []) if t.get("status") != "done"]
        if not open_tasks:
            clear_mode(state, chat_id)
            tg.send(chat_id, "Открытых задач нет.")
            return True
        set_mode(state, chat_id, "awaiting_done")
        tg.send(chat_id, queue_text(state) + "\n\nНапиши номер задачи, которую закрыть.")
        return True
    if text == "↩️ Отмена":
        clear_mode(state, chat_id)
        tg.send(chat_id, "Ок, отменил.")
        return True
    return False


def handle_mode(tg: Telegram, state: dict[str, Any], chat_id: int, text: str) -> bool:
    mode = get_mode(state, chat_id)
    kind = mode.get("mode")
    data = mode.get("data") or {}
    if kind == "awaiting_task":
        owner = str(data.get("owner") or "claude")
        task = add_task(state, text if text.lstrip().startswith("[") else f"[{owner}] {text}")
        mark_notified(state, task)
        clear_mode(state, chat_id)
        tg.send(
            chat_id,
            task_notice(task["owner"], task["id"], "Задачу принял", "Агент начнёт работу, когда дойдёт очередь."),
            html_mode=True,
            reply_markup=task_actions_keyboard(task["id"]),
        )
        return True
    if kind == "awaiting_clarify":
        task = task_by_id(state, int(data.get("task_id") or 0))
        clear_mode(state, chat_id)
        if not task or task.get("status") in TERMINAL_TASK_STATUSES:
            tg.send(chat_id, "Задача уже закрыта — уточнение не применить.")
            return True
        task["text"] = f"{task.get('text', '')}\n\nУточнение от пользователя: {text}"
        append_task_chat(task, "user", f"Clarification: {text}")
        append_compact_context("user", f"Task #{task['id']} clarification: {text}")
        add_event(state, f"Task #{task['id']} clarified")
        save_state(state)
        tg.send(chat_id, f"Уточнение добавлено к задаче #{task['id']}.")
        return True
    if kind == "awaiting_done":
        if not text.strip().isdigit():
            tg.send(chat_id, "Нужен номер задачи. Например: 12")
            return True
        ok = mark_done(state, int(text.strip()))
        clear_mode(state, chat_id)
        tg.send(
            chat_id,
            task_notice("Codex", None, "Задача закрыта" if ok else "Задача не найдена", "Готово." if ok else "Проверь номер задачи.", ok=ok),
            html_mode=True,
        )
        return True
    if kind == "awaiting_answer":
        pending = [q for q in state.get("questions", []) if q.get("status") == "pending"]
        qid = None
        answer = text.strip()
        head, _, rest = answer.partition(" ")
        if head.isdigit():
            qid = int(head)
            answer = rest.strip()
        elif len(pending) == 1:
            qid = int(pending[0]["id"])
        if not qid or not answer:
            tg.send(chat_id, "Нужно: номер и текст ответа. Если вопрос один — просто текст ответа.")
            return True
        ok = answer_question(state, qid, answer)
        clear_mode(state, chat_id)
        tg.send(chat_id, "Ответ сохранён. Агент продолжит задачу." if ok else "Вопрос не найден.")
        return True
    return False


def add_task_from_text(tg: Telegram, state: dict[str, Any], chat_id: int, text: str, owner: str) -> None:
    task = add_task(state, f"[{owner}] {text}")
    mark_notified(state, task)
    clear_mode(state, chat_id)
    tg.send(
        chat_id,
        task_notice(task["owner"], task["id"], "Задачу принял", "Агент начнёт работу, когда дойдёт очередь."),
        html_mode=True,
        reply_markup=task_actions_keyboard(task["id"]),
    )


def handle_voice(tg: Telegram, state: dict[str, Any], chat_id: int, voice: dict[str, Any]) -> None:
    mode = get_mode(state, chat_id)
    owner = str((mode.get("data") or {}).get("owner") or "claude")
    tg.send(chat_id, "Расшифровываю голосовое...")
    text = transcribe_voice(tg, str(voice.get("file_id") or ""))
    add_task_from_text(tg, state, chat_id, text, owner)


def handle_message(tg: Telegram, state: dict[str, Any], message: dict[str, Any]) -> None:
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    user_id = (message.get("from") or {}).get("id")
    text = (message.get("text") or "").strip()
    voice = message.get("voice")
    if not chat_id or (not text and not voice):
        return
    if not user_allowed(int(user_id) if user_id is not None else None):
        tg.send(chat_id, "Доступ закрыт.")
        return
    if text.startswith("/start"):
        claimed = claim_owner_if_empty(state, int(chat_id))
        if claimed or owner_allowed(state, int(chat_id)):
            tg.send(chat_id, "Бот подключён к {{PROJECT_NAME}}.\n\n" + HELP)
        else:
            tg.send(chat_id, "Этот бот уже привязан к другому чату.")
        return
    if not owner_allowed(state, int(chat_id)):
        tg.send(chat_id, "Доступ закрыт.")
        return
    reply_qid = question_id_from_reply(message)
    if reply_qid and (text or voice):
        try:
            answer = text or transcribe_voice(tg, str(voice.get("file_id") or ""))
        except Exception as exc:
            tg.send(chat_id, f"Не смог расшифровать ответ: {type(exc).__name__}. Лучше ответь текстом.")
            return
        ok = answer_question(state, reply_qid, answer)
        tg.send(chat_id, "Ответ сохранён. Агент продолжит задачу." if ok else "Вопрос не найден.")
        return
    if voice:
        try:
            handle_voice(tg, state, int(chat_id), voice)
        except Exception as exc:
            tg.send(chat_id, f"Не смог расшифровать голосовое: {type(exc).__name__}. Лучше отправь текстом.")
        return
    if handle_button(tg, state, int(chat_id), text):
        return
    if not text.startswith("/") and handle_mode(tg, state, int(chat_id), text):
        return
    if text.startswith("/"):
        tg.send(chat_id, "Используй кнопки ниже.")
        return
    task = add_task(state, text)
    mark_notified(state, task)
    tg.send(
        chat_id,
        task_notice(task["owner"], task["id"], "Задачу принял", "Агент начнёт работу, когда дойдёт очередь."),
        html_mode=True,
        reply_markup=task_actions_keyboard(task["id"]),
    )


def handle_callback_query(tg: Telegram, state: dict[str, Any], callback: dict[str, Any]) -> None:
    query_id = str(callback.get("id") or "")
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    user_id = (callback.get("from") or {}).get("id")
    data = str(callback.get("data") or "")
    if not query_id or not chat_id:
        return
    if not user_allowed(int(user_id) if user_id is not None else None) or not owner_allowed(state, int(chat_id)):
        tg.answer_callback(query_id, "Доступ закрыт.")
        return
    message_id = message.get("message_id")
    if data.startswith("cancel_task:"):
        raw_task_id = data.split(":", 1)[1]
        if not raw_task_id.isdigit():
            tg.answer_callback(query_id, "Некорректная задача.")
            return
        ok = cancel_task(state, int(raw_task_id), actor="telegram")
        tg.answer_callback(query_id, "Задача отменена." if ok else "Активная задача не найдена.")
        if ok and message_id:
            tg.edit_reply_markup(chat_id, message_id)  # снять кнопки, карточка очереди обновится сама
        return
    if data.startswith("prio_task:"):
        raw_task_id = data.split(":", 1)[1]
        task = task_by_id(state, int(raw_task_id)) if raw_task_id.isdigit() else None
        if not task:
            tg.answer_callback(query_id, "Задача не найдена.", show_alert=True)
            return
        status = str(task.get("status") or "open")
        if status != "open":
            reason = {
                "claimed": f"Задача #{task['id']} уже В РАБОТЕ у агента — приоритет менять поздно.",
                "done": f"Задача #{task['id']} уже завершена.",
                "cancelled": f"Задача #{task['id']} отменена.",
            }.get(status, f"Задача #{task['id']} не в очереди (статус: {status}).")
            tg.answer_callback(query_id, reason, show_alert=True)
            return
        task["priority"] = True
        add_event(state, f"Task #{task['id']} prioritized")
        save_state(state)
        tg.answer_callback(query_id, f"Готово: #{task['id']} первая в очереди.")
        if message_id:
            base = str(message.get("text") or "").strip()
            marker = "❗ ПРИОРИТЕТ"
            if marker not in base:
                tg.edit_message(
                    chat_id,
                    message_id,
                    f"{base}\n\n{marker}: задача поднята в начало очереди.",
                    reply_markup=task_actions_keyboard(task["id"]),
                )
        return
    if data.startswith("clarify_task:"):
        raw_task_id = data.split(":", 1)[1]
        task = task_by_id(state, int(raw_task_id)) if raw_task_id.isdigit() else None
        if not task or task.get("status") in TERMINAL_TASK_STATUSES:
            tg.answer_callback(query_id, "Задача уже закрыта.")
            return
        set_mode(state, int(chat_id), "awaiting_clarify", task_id=task["id"])
        tg.answer_callback(query_id)
        tg.send(chat_id, f"Напиши уточнение к задаче #{task['id']}.")
        return
    if data.startswith("qopt:"):
        rest = data.split(":", 1)[1]
        qid_s, _, idx_s = rest.partition(":")
        question = None
        if qid_s.isdigit():
            for q in state.get("questions", []):
                if q.get("id") == int(qid_s):
                    question = q
                    break
        options = (question or {}).get("options") or []
        if not question or not idx_s.isdigit() or int(idx_s) >= len(options):
            tg.answer_callback(query_id, "Вариант не найден.")
            return
        if question.get("status") != "pending":
            tg.answer_callback(query_id, "Вопрос уже отвечен.")
            return
        option = str(options[int(idx_s)])
        answer_question(state, int(qid_s), option)
        tg.answer_callback(query_id, "Ответ принят.")
        if message_id:
            base = str(message.get("text") or "").strip()
            tg.edit_message(chat_id, message_id, f"{base}\n\n✅ Ответ: {option}")
        return
    tg.answer_callback(query_id, "Неизвестная кнопка.")


def run_bot() -> None:
    token = bot_token()
    if not token:
        raise SystemExit("WORKER_BOT_TOKEN is not set")
    tg = Telegram(token)
    state = load_state()
    save_state(state)
    print(f"Worker bot running. Inbox: {INBOX_FILE}")
    prev_active_tasks: int | None = None
    while True:
        try:
            with state_lock():
                state = load_state()
                offset = int(state.get("last_update_id") or 0) + 1
            updates = tg.updates(offset)
            with state_lock():
                state = load_state()
                for update in updates:
                    state["last_update_id"] = max(int(state.get("last_update_id") or 0), int(update.get("update_id") or 0))
                    callback = update.get("callback_query")
                    if callback:
                        handle_callback_query(tg, state, callback)
                    message = update.get("message") or update.get("edited_message")
                    if message:
                        handle_message(tg, state, message)
                dispatch_open_tasks(tg, state)
                send_working_heartbeat(tg, state)
                refresh_queue_card(tg, state)
                now_active = count_active_tasks(state)
                notify_queue_empty(tg, state, prev_active_tasks, now_active)
                prev_active_tasks = now_active
                save_state(state)
        except urllib.error.URLError as exc:
            print(f"telegram network error: {type(exc).__name__}", file=sys.stderr)
            time.sleep(5)
        except KeyboardInterrupt:
            print("Stopped.")
            return
        except Exception as exc:
            print(f"worker bot error: {type(exc).__name__}: {exc}", file=sys.stderr)
            time.sleep(5)


def notify_owner(text: str, *, html_mode: bool = False, reply_markup: dict[str, Any] | None = None) -> None:
    token = bot_token()
    state = load_state()
    owner = str(state.get("owner_chat_id") or "").strip()
    if token and owner:
        Telegram(token).send(owner, text, html_mode=html_mode, reply_markup=reply_markup)


def notify_owner_photo(photo_path: str, caption: str = "") -> None:
    token = bot_token()
    state = load_state()
    owner = str(state.get("owner_chat_id") or "").strip()
    if token and owner:
        Telegram(token).send_photo(owner, photo_path, caption=caption)


def context_text(state: dict[str, Any], agent: str) -> str:
    parts: list[str] = []
    if COMPACT_CONTEXT_FILE.exists():
        text = COMPACT_CONTEXT_FILE.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            parts.append("# Worker Bot Compact Context\n\n" + text)
    path = agent_chat_file(agent)
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            parts.append("# Agent Chat\n\n" + text)
    return "\n\n".join(parts).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Telegram worker bot")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("check")
    status_p = sub.add_parser("status")
    status_p.add_argument("agent")
    status_p.add_argument("text", nargs="+")
    ask_p = sub.add_parser("ask")
    ask_p.add_argument("agent")
    ask_p.add_argument("text", nargs="+")
    ask_p.add_argument("--options", default="", help="Варианты ответа через |, станут кнопками")
    add_p = sub.add_parser("add")
    add_p.add_argument("agent")
    add_p.add_argument("text", nargs="+")
    done_p = sub.add_parser("done")
    done_p.add_argument("task_id", type=int)
    release_p = sub.add_parser("release")
    release_p.add_argument("task_id", type=int)
    release_p.add_argument("reason", nargs="*")
    next_p = sub.add_parser("next")
    next_p.add_argument("agent")
    hook_p = sub.add_parser("hook")
    hook_p.add_argument("agent")
    context_p = sub.add_parser("context")
    context_p.add_argument("agent")
    photo_p = sub.add_parser("photo")
    photo_p.add_argument("agent")
    photo_p.add_argument("path")
    photo_p.add_argument("caption", nargs="*")
    sub.add_parser("render")
    sub.add_parser("queue")
    args = parser.parse_args()

    if args.cmd == "run":
        run_bot()
        return
    if args.cmd == "check":
        token = bot_token()
        if not token:
            raise SystemExit("WORKER_BOT_TOKEN is not set")
        me = Telegram(token).me()
        username = me.get("username") or me.get("first_name") or me.get("id")
        print(f"Telegram bot OK: {username}")
        return

    if args.cmd == "status":
        text = " ".join(args.text)
        with state_lock():
            state = load_state()
            set_status(state, args.agent, text)
        notify_owner(
        task_notice(args.agent, None, "Задачу принял и работает" if "Взял задачу" in text else "Статус обновлён", text),
            html_mode=True,
        )
    elif args.cmd == "photo":
        caption = " ".join(args.caption)
        notify_owner_photo(args.path, caption=f"[{args.agent}] {caption}" if caption else f"[{args.agent}]")
        print("photo sent")
    elif args.cmd == "ask":
        text = " ".join(args.text)
        options = [o.strip() for o in (args.options or "").split("|") if o.strip()][:6]
        with state_lock():
            state = load_state()
            question = add_question(state, args.agent, text, options=options)
        if options:
            markup = {
                "inline_keyboard": [
                    [{"text": f"{i + 1}. {opt}"[:40], "callback_data": f"qopt:{question['id']}:{i}"}]
                    for i, opt in enumerate(options)
                ]
            }
        else:
            markup = {"force_reply": True, "selective": True, "input_field_placeholder": "Ответ агенту"}
        notify_owner(question_notice(args.agent, question["id"], text, options=options), html_mode=True, reply_markup=markup)
        print(f"Q{question['id']}")
    elif args.cmd == "add":
        text = " ".join(args.text)
        with state_lock():
            state = load_state()
            task = add_task(state, f"[{args.agent}] {text}")
        notify_owner(task_notice(task["owner"], None, "Задачу принял", "Агент начнёт работу, когда дойдёт очередь."), html_mode=True)
        print(f"#{task['id']}")
    elif args.cmd == "done":
        with state_lock():
            state = load_state()
            task = task_by_id(state, args.task_id)
            if not mark_done(state, args.task_id):
                raise SystemExit(f"Task #{args.task_id} not found")
        notify_owner(task_notice((task or {}).get("owner", "Codex"), None, "Задача закрыта", "Готово."), html_mode=True)
    elif args.cmd == "release":
        reason = " ".join(args.reason).strip()
        with state_lock():
            state = load_state()
            if not release_task(state, args.task_id, reason):
                raise SystemExit(f"Task #{args.task_id} is not claimed")
        print("OK")

    elif args.cmd == "next":
        with state_lock():
            state = load_state()
            task = claim_next_task(state, args.agent)
        if not task:
            print("NO_TASK")
            return
        write_current_task(args.agent, task)
        print(f"#{task['id']} [{task.get('owner', 'claude')}] {task.get('text', '')}")
    elif args.cmd == "hook":
        with state_lock():
            state = load_state()
            text = hook_context(state, args.agent)
        if text:
            print(text)
    elif args.cmd == "context":
        state = load_state()
        text = context_text(state, args.agent)
        if text:
            print(text)
    elif args.cmd == "render":
        with state_lock():
            state = load_state()
            save_state(state)
        print(INBOX_FILE)
    elif args.cmd == "queue":
        state = load_state()
        print(queue_text(state))


if __name__ == "__main__":
    main()
