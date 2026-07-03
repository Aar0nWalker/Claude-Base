"""ARQ worker skeleton. Add real background tasks as async functions below and
list them in FUNCTIONS. Run with: arq app.worker.WorkerSettings
"""
import logging

from arq.connections import RedisSettings

from .config import settings
from .media_cleanup import retry_pending_media_deletes
from .queues import DEFAULT_QUEUE

logger = logging.getLogger(__name__)


async def cleanup_pending_media_deletes_task(ctx):
    deleted, pending = await retry_pending_media_deletes()
    return {"deleted": deleted, "pending": pending}


async def _on_startup(ctx):
    logger.info("worker started")


FUNCTIONS = [
    cleanup_pending_media_deletes_task,
]


class WorkerSettings:
    functions = FUNCTIONS
    queue_name = DEFAULT_QUEUE
    on_startup = _on_startup
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 1800
    max_tries = 3
