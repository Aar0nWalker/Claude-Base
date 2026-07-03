from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_session():
    async with SessionLocal() as session:
        yield session


async def create_tables():
    from . import models  # noqa: registers models with Base
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_user_action_events_created_at ON user_action_events (created_at)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_user_action_events_user_created ON user_action_events (user_id, created_at)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_user_action_events_session_created ON user_action_events (session_id, created_at)"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_pending_media_deletes_file_url "
            "ON pending_media_deletes (file_url)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_pending_media_deletes_attempts_created "
            "ON pending_media_deletes (attempts, created_at)"
        ))
        # add future idempotent migrations here (ALTER TABLE ... ADD COLUMN IF NOT EXISTS, etc.)
