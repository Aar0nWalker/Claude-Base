"""Test harness — runs against an isolated in-memory SQLite DB and fully mocked
external services. NEVER touches production Postgres, SMTP, S3 or Redis.
"""
import os
import tempfile

# ── Isolate the environment BEFORE importing the app ────────────────────────
# The app builds its engine/Settings at import time from these env vars. Point
# everything at throwaway local values so importing the app can never reach prod.
_TMP_STORAGE = tempfile.mkdtemp(prefix="apptest_storage_")
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "JWT_SECRET": "test-secret-not-prod",
    "ADMIN_EMAIL": "admin@test.local",
    "ADMIN_PASSWORD": "admin-pass",
    "STORAGE_PATH": _TMP_STORAGE,
    "REDIS_URL": "redis://localhost:6379",  # never connected (slots are mocked)
})

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.db import Base, get_session
from app.main import app
from app.routers.auth import _hash, _make_token
from app.models import User

# ── Data-safety guard ───────────────────────────────────────────────────────
# Refuse to run if the test DB isn't an obviously-disposable one. Protects
# against ever pointing the suite at a real database.
assert "sqlite" in settings.database_url, (
    f"REFUSING TO RUN: tests must use a disposable sqlite DB, got {settings.database_url!r}"
)

# Temp-file SQLite so the request session and the test session use SEPARATE
# connections to the SAME db (no single-connection async contention), while
# committed data stays visible across them.
_DB_FILE = os.path.join(tempfile.mkdtemp(prefix="apptest_db_"), "test.db")
test_engine = create_async_engine(f"sqlite+aiosqlite:///{_DB_FILE}")
TestSession = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
async def _schema():
    """Fresh schema per test → full isolation."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    async with TestSession() as s:
        yield s


@pytest_asyncio.fixture(autouse=True)
async def _override_session():
    async def _get_session():
        async with TestSession() as s:
            yield s
    app.dependency_overrides[get_session] = _get_session
    yield
    app.dependency_overrides.pop(get_session, None)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Mock all external services (autouse) ────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_externals(monkeypatch):
    # Disable rate limiting — all tests share one client IP, limits would trip.
    from app.limiter import limiter
    monkeypatch.setattr(limiter, "enabled", False, raising=False)

    sent_emails: list = []

    async def _fake_send(to, subject, html, text):
        sent_emails.append({"to": to, "subject": subject})

    monkeypatch.setattr("app.email._send", _fake_send, raising=False)
    # auth.py imports send_* functions by name; email._send is patched above so
    # every send_*_email() call in auth/admin routes goes through the fake.

    return {"emails": sent_emails}


# ── Helpers ─────────────────────────────────────────────────────────────────
async def make_user(session, email="user@test.local", admin=False, verified=True, password="pw"):
    if admin:
        email = settings.admin_email
    u = User(email=email, hashed_password=_hash(password), email_verified=verified)
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


def auth_headers(user: User):
    token = _make_token(user.id, user.email, token_version=user.token_version)
    return {"Authorization": f"Bearer {token}"}


async def reload_user(user_id: int) -> User:
    """Read a user through a FRESH session — avoids stale identity-map values and
    connection-state issues after a request mutated the row on another session."""
    async with TestSession() as s:
        return await s.get(User, user_id)
