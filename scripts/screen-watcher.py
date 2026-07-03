"""Windows-side screen watcher for the Telegram worker bot.

Polls .agents/worker-bot/screen_request.json (written by the bot when the owner
presses "Скрин экрана" / "Скрин VS Code"), captures the desktop or the VS Code
window, and sends the PNG straight to the owner chat via the Bot API.

Runs on the HOST (the bot itself lives in Docker and cannot see the screen).
Start:  pythonw scripts\\screen-watcher.py   (or scripts\\screen-watcher.bat)
Needs:  pillow. Token/owner come from .env + state.json, never printed.
"""
import ctypes
import ctypes.wintypes
import json
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".agents" / "worker-bot"
REQUEST = STATE_DIR / "screen_request.json"
SHOTS = STATE_DIR / "screenshots"
LOG = STATE_DIR / "screen-watcher.log"

ctypes.windll.user32.SetProcessDPIAware()  # ponytail: per-monitor DPI v2 if multi-monitor scaling ever misbehaves


def log(msg: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{stamp} {msg}\n")


def read_env() -> dict[str, str]:
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def vscode_bbox() -> tuple[int, int, int, int] | None:
    """Rect of the first visible window whose title mentions Visual Studio Code."""
    user32 = ctypes.windll.user32
    found: list[tuple[int, int, int, int]] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if "Visual Studio Code" in buf.value:
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            if rect.right - rect.left > 100 and rect.bottom - rect.top > 100:
                found.append((rect.left, rect.top, rect.right, rect.bottom))
                return False
        return True

    user32.EnumWindows(enum_cb, None)
    return found[0] if found else None


def send_photo(token: str, chat_id: str, path: Path, caption: str, proxy: str = "") -> None:
    boundary = uuid.uuid4().hex
    content = path.read_bytes()
    parts = []
    for name, value in (("chat_id", chat_id), ("caption", caption[:1024])):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="{path.name}"\r\n'
        f"Content-Type: image/png\r\n\r\n".encode() + content + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"https": proxy, "http": proxy} if proxy else {})
    )
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with opener.open(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")


def main() -> None:
    env = read_env()
    token = env.get("WORKER_BOT_TOKEN", "")
    proxy = env.get("WORKER_BOT_PROXY_URL", "")
    if not token:
        log("no WORKER_BOT_TOKEN in .env, exiting")
        return
    SHOTS.mkdir(parents=True, exist_ok=True)
    log("screen watcher started")
    while True:
        try:
            if REQUEST.exists():
                req = json.loads(REQUEST.read_text(encoding="utf-8"))
                REQUEST.unlink()
                target = str(req.get("target") or "desktop")
                state = json.loads((STATE_DIR / "state.json").read_text(encoding="utf-8"))
                owner = str(state.get("owner_chat_id") or "")
                if not owner:
                    log("no owner_chat_id, skip")
                    continue
                bbox = vscode_bbox() if target == "vscode" else None
                caption = "Скрин VS Code" if (target == "vscode" and bbox) else (
                    "Окно VS Code не нашёл — весь экран" if target == "vscode" else "Скрин рабочего стола"
                )
                img = ImageGrab.grab(bbox=bbox, all_screens=(bbox is None))
                shot = SHOTS / f"scr-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.png"
                img.save(shot)
                send_photo(token, owner, shot, caption, proxy=proxy)
                log(f"sent {shot.name} ({target})")
        except Exception as exc:  # noqa: BLE001 — watcher must survive anything
            log(f"error: {type(exc).__name__}: {exc}")
            time.sleep(5)
        time.sleep(2)


if __name__ == "__main__":
    main()
