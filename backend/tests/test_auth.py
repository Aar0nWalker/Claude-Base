import pytest
from conftest import make_user, auth_headers
from app.deps import SESSION_COOKIE_NAME
from app.routers.auth import _make_token
from app.models import User, AppSetting
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def test_register_new_user(client, session, mock_externals):
    r = await client.post("/auth/register", json={"email": "new@yandex.ru", "password": "password123"})
    assert r.status_code == 200
    assert r.json() == {"status": "verify_email_sent"}
    u = await session.scalar(select(User).where(User.email == "new@yandex.ru"))
    assert u is not None and not u.email_verified


async def test_register_saves_onboarding_generation_context(client, session, mock_externals):
    r = await client.post("/auth/register", json={
        "email": "ctx@yandex.ru",
        "password": "password123",
        "role": "Маркетолог",
        "video_use": "Видео для соцсетей",
        "onboarding_note": "Нужен живой UGC без рекламного тона",
        "company_context": "Бренд косметики для молодой аудитории",
        "product_context": "Важно показывать текстуру и оттенки",
        "reference_urls": "https://example.com/ref",
    })
    assert r.status_code == 200
    u = await session.scalar(select(User).where(User.email == "ctx@yandex.ru"))
    assert u is not None
    assert u.onboarding_role == "Маркетолог"
    assert u.onboarding_video_use == "Видео для соцсетей"
    assert u.onboarding_note == "Нужен живой UGC без рекламного тона"
    assert u.company_context == "Бренд косметики для молодой аудитории"
    assert u.product_context == "Важно показывать текстуру и оттенки"
    assert u.reference_urls == "https://example.com/ref"


async def test_register_existing_does_not_reveal(client, session):
    await make_user(session, email="dup@yandex.ru", verified=True)
    r = await client.post("/auth/register", json={"email": "dup@yandex.ru", "password": "password123"})
    # Same response as a fresh signup — no enumeration.
    assert r.status_code == 200
    assert r.json() == {"status": "verify_email_sent"}


async def test_register_waitlisted_when_closed(client, session, mock_externals):
    # Registrations closed → sign-up is waitlisted: recorded, no email, no token.
    session.add(AppSetting(key="registration_open", value="0"))
    await session.commit()
    r = await client.post("/auth/register", json={"email": "wait@yandex.ru", "password": "password123"})
    assert r.status_code == 200
    assert r.json() == {"status": "waitlisted"}
    u = await session.scalar(select(User).where(User.email == "wait@yandex.ru"))
    assert u is not None and u.waitlisted and not u.email_verified
    assert u.verification_token is None  # no verification email issued while closed


async def test_register_short_password(client):
    r = await client.post("/auth/register", json={"email": "x@example.com", "password": "short"})
    assert r.status_code == 400


async def test_login_ok(client, session):
    await make_user(session, email="log@example.com", password="password123", verified=True)
    r = await client.post("/auth/login", json={"email": "log@example.com", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["email"] == "log@example.com"
    assert SESSION_COOKIE_NAME in r.cookies
    assert (await client.get("/auth/me")).json()["email"] == "log@example.com"


async def test_cookie_mutation_rejects_bad_origin(client, session):
    await make_user(session, email="csrf@example.com", password="password123", verified=True)
    r = await client.post("/auth/login", json={"email": "csrf@example.com", "password": "password123"})
    assert r.status_code == 200
    bad = await client.post("/auth/logout", headers={"Origin": "https://evil.example"})
    assert bad.status_code == 403
    ok = await client.post("/auth/logout", headers={"Origin": "http://localhost:3000"})
    assert ok.status_code == 200


async def test_login_email_case_insensitive(client, session):
    # Registered with a capitalized email (mobile keyboards auto-capitalize) →
    # must still log in with any case. Regression for the "verified but not let in" bug.
    await make_user(session, email="Mixed@Example.com", password="password123", verified=True)
    r = await client.post("/auth/login", json={"email": "mixed@example.com", "password": "password123"})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "Mixed@Example.com"
    assert SESSION_COOKIE_NAME in r.cookies


async def test_register_lowercases_email(client, session):
    r = await client.post("/auth/register", json={"email": "CapsUser@Yandex.ru", "password": "password123"})
    assert r.status_code == 200
    # Stored lowercased so future lookups match regardless of typed case.
    u = await session.scalar(select(User).where(User.email == "capsuser@yandex.ru"))
    assert u is not None


async def test_login_wrong_password(client, session):
    await make_user(session, email="log2@example.com", password="password123", verified=True)
    r = await client.post("/auth/login", json={"email": "log2@example.com", "password": "WRONG"})
    assert r.status_code == 401


async def test_login_unverified(client, session):
    await make_user(session, email="unv@example.com", password="password123", verified=False)
    r = await client.post("/auth/login", json={"email": "unv@example.com", "password": "password123"})
    assert r.status_code == 403


async def test_jwt_required_and_invalid(client):
    # No token
    assert (await client.get("/auth/me")).status_code in (401, 403)
    # Garbage token
    r = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


async def test_token_version_invalidates_old_token(client, session):
    u = await make_user(session, email="tv@example.com", verified=True)
    old = {"Authorization": f"Bearer {_make_token(u.id, u.email, token_version=0)}"}
    # bump token_version (simulates password change/reset)
    u.token_version = 1
    await session.commit()
    r = await client.get("/auth/me", headers=old)
    assert r.status_code == 401


async def test_verification_throttle_blocks_after_three(client, session):
    # 1st register sends; re-registering an unverified user resends with escalating
    # cooldown, then a hard 429 block.
    email = "thr@yandex.ru"
    r1 = await client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r1.status_code == 200
    # immediate re-register → cooldown not elapsed → 429 block message
    r2 = await client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r2.status_code == 429
