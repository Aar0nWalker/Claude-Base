import asyncio
import os
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .config import settings

BACKUP_DIR = Path("/backups")
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MAX_BACKUPS = 3


def _parse_db_url(url: str) -> dict:
    clean = url.replace("postgresql+asyncpg://", "postgresql://")
    p = urlparse(clean)
    return {
        "host": p.hostname or "localhost",
        "port": str(p.port or 5432),
        "user": p.username or "",
        "password": p.password or "",
        "dbname": p.path.lstrip("/"),
    }


async def run_backup() -> None:
    db = _parse_db_url(settings.database_url)
    ts = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    dest = BACKUP_DIR / ts
    dest.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "PGPASSWORD": db["password"]}
    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-h", db["host"],
        "-p", db["port"],
        "-U", db["user"],
        "-d", db["dbname"],
        "-f", str(dest / "db.sql"),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        print(f"[backup] pg_dump FAILED: {stderr.decode()}", flush=True)
        shutil.rmtree(dest, ignore_errors=True)
        return

    if PROMPTS_DIR.exists():
        shutil.copytree(PROMPTS_DIR, dest / "prompts")

    backups = sorted(p for p in BACKUP_DIR.iterdir() if p.is_dir())
    for old in backups[:-MAX_BACKUPS]:
        shutil.rmtree(old, ignore_errors=True)

    print(f"[backup] done -> {dest}", flush=True)


async def backup_loop() -> None:
    while True:
        await asyncio.sleep(3600)
        try:
            await run_backup()
        except Exception as exc:
            print(f"[backup] ERROR: {exc}", flush=True)
