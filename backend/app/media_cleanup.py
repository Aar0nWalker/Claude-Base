"""Retry queue for media deletes that failed after DB rows were removed."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from arq.connections import RedisSettings, create_pool

from .config import settings
from .db import SessionLocal
from .models import PendingMediaDelete
from .queues import DEFAULT_QUEUE
from .storage import delete_media

logger = logging.getLogger(__name__)


async def record_pending_media_delete(
    session: AsyncSession,
    file_url: str | None,
    *,
    user_id: int | None = None,
    source: str = "",
    error: str | None = None,
) -> None:
    if not file_url:
        return
    row = await session.scalar(
        select(PendingMediaDelete).where(PendingMediaDelete.file_url == file_url)
    )
    if row:
        row.source = source or row.source
        row.user_id = user_id or row.user_id
        row.last_error = (error or row.last_error or "")[:1000]
        row.updated_at = datetime.utcnow()
        return
    session.add(
        PendingMediaDelete(
            file_url=file_url,
            user_id=user_id,
            source=source[:80],
            last_error=(error or "")[:1000],
        )
    )


async def retry_pending_media_deletes(limit: int = 100) -> tuple[int, int]:
    """Retry pending media deletes. Returns (deleted, still_pending)."""
    deleted = 0
    pending = 0
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(PendingMediaDelete)
                .where(PendingMediaDelete.attempts < 50)
                .order_by(PendingMediaDelete.created_at.asc())
                .limit(max(1, min(limit, 500)))
            )
        ).scalars().all()
        for row in rows:
            row.attempts += 1
            row.updated_at = datetime.utcnow()
            ok = await delete_media(row.file_url, settings.storage_path)
            if ok:
                await session.delete(row)
                deleted += 1
            else:
                row.last_error = "delete_media returned false"
                pending += 1
        await session.commit()
    if deleted or pending:
        logger.info("pending media delete retry: deleted=%s pending=%s", deleted, pending)
    return deleted, pending


async def enqueue_pending_media_cleanup() -> None:
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await pool.enqueue_job("cleanup_pending_media_deletes_task", _queue_name=DEFAULT_QUEUE)
    finally:
        await pool.aclose()
