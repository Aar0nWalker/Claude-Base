import asyncio
import logging
import math
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import bcrypt as _bcrypt
from jose import jwt
from pydantic import BaseModel, EmailStr, Field

from ..config import settings
from ..db import get_session
from ..deps import SESSION_COOKIE_NAME, get_current_user, registration_open
from ..email import send_verification_email, send_reset_email, send_onboarding_email
from ..limiter import limiter
from ..models import User

router = APIRouter()

logger = logging.getLogger(__name__)


def _fire_and_forget(coro, label: str) -> None:
    """Run a background coroutine (email send) without awaiting it, logging any
    failure. Raw asyncio.create_task drops exceptions silently when the task is
    never awaited, so a broken SMTP/network would fail invisibly."""
    async def _runner() -> None:
        try:
            await coro
        except Exception:
            logger.exception("background task failed: %s", label)
    asyncio.create_task(_runner())


# ponytail: RU-only email allowlist is a business policy inherited from the
# source project, not framework logic. Loosen/remove when this template is
# used for a non-RU audience.
ALLOWED_PUBLIC_EMAIL_DOMAINS = {
    "yandex.ru", "ya.ru", "mail.ru", "bk.ru", "inbox.ru", "list.ru",
    "internet.ru", "rambler.ru", "lenta.ru", "autorambler.ru", "myrambler.ru",
    "ro.ru", "vk.com", "corp.mail.ru", "tbank.ru", "sber.ru",
}
ALLOWED_CORPORATE_EMAIL_TLDS = (".ru", ".su", ".рф")
RU_EMAIL_MESSAGE = (
    "Для регистрации используйте российскую почту: Яндекс, Mail.ru, Rambler, VK, "
    "T-Bank, Sber или корпоративный домен .ru, .su, .рф."
)


def _is_allowed_registration_email(email: str) -> bool:
    domain = email.rsplit("@", 1)[-1].strip().lower().rstrip(".")
    if domain in ALLOWED_PUBLIC_EMAIL_DOMAINS:
        return True
    return domain.endswith(ALLOWED_CORPORATE_EMAIL_TLDS)


def _hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())


async def _hash_async(password: str) -> str:
    return await asyncio.to_thread(_hash, password)


async def _verify_async(password: str, hashed: str) -> bool:
    return await asyncio.to_thread(_verify, password, hashed)


# password capped at 128 — bcrypt truncates at 72 bytes anyway, and the cap
# stops a multi-MB string from reaching the (deliberately slow) bcrypt hasher
class AuthRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(max_length=128)
    role: str | None = Field(None, max_length=120)
    video_use: str | None = Field(None, max_length=800)
    onboarding_note: str | None = Field(None, max_length=800)
    company_context: str | None = Field(None, max_length=1500)
    product_context: str | None = Field(None, max_length=1500)
    reference_urls: str | None = Field(None, max_length=1500)


def _clean_optional_text(value: str | None, limit: int) -> str | None:
    text = (value or "").strip()
    return text[:limit] if text else None


def _apply_onboarding_context(user: User, req: AuthRequest) -> None:
    user.onboarding_role = _clean_optional_text(req.role, 120)
    user.onboarding_video_use = _clean_optional_text(req.video_use, 800)
    user.onboarding_note = _clean_optional_text(req.onboarding_note, 800)
    user.company_context = _clean_optional_text(req.company_context, 1500)
    user.product_context = _clean_optional_text(req.product_context, 1500)
    user.reference_urls = _clean_optional_text(req.reference_urls, 1500)


class SessionResponse(BaseModel):
    ok: bool = True
    email: str
    is_admin: bool
    onboarding_role: str | None = None
    onboarding_video_use: str | None = None
    onboarding_note: str | None = None
    company_context: str | None = None
    product_context: str | None = None
    reference_urls: str | None = None


class OkResponse(BaseModel):
    ok: bool = True


# Outbound-email throttle (verification + password reset). A user may receive at
# most this many emails of a given kind; each send opens an escalating cooldown
# before the next is allowed: 1st free → 10m → 30m → 60m → hard stop (→ support).
MAX_EMAIL_SENDS = 3
_EMAIL_COOLDOWN_MIN = {1: 10, 2: 30, 3: 60}  # minutes to wait after the Nth send


def _email_throttle_message(count: int, last: datetime | None, *, what: str) -> str | None:
    """Returns a Russian message to show the user (and skip the send) when the
    send must be blocked, or None when a send is allowed. `what` names the action
    in the limit message (e.g. "подтверждения email", "сброса пароля")."""
    count = count or 0
    # Inside the cooldown window after the previous send → ask the user to wait.
    if count >= 1 and last is not None:
        cd_min = _EMAIL_COOLDOWN_MIN.get(min(count, 3), 60)
        remaining = timedelta(minutes=cd_min) - (datetime.utcnow() - last)
        if remaining.total_seconds() > 0:
            mins = math.ceil(remaining.total_seconds() / 60)
            return f"Письмо уже отправлено. Повторить можно через {mins} мин."
    # Cooldown elapsed (or first send). Past the limit → permanent stop.
    if count >= MAX_EMAIL_SENDS:
        addr = settings.support_email or settings.mail_from or settings.admin_email
        return f"Слишком много попыток {what}. Напишите нам на {addr} — поможем."
    return None


def _verification_block_message(user: User) -> str | None:
    return _email_throttle_message(
        user.verification_send_count, user.verification_last_sent, what="подтверждения email"
    )


def _record_verification_send(user: User) -> None:
    user.verification_send_count = (user.verification_send_count or 0) + 1
    user.verification_last_sent = datetime.utcnow()


def _reset_block_message(user: User) -> str | None:
    return _email_throttle_message(
        user.reset_send_count, user.reset_last_sent, what="сброса пароля"
    )


def _record_reset_send(user: User) -> None:
    user.reset_send_count = (user.reset_send_count or 0) + 1
    user.reset_last_sent = datetime.utcnow()


def _make_token(user_id: int, email: str, token_version: int = 0) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    is_admin = bool(settings.admin_email and email == settings.admin_email)
    # NOTE: `is_admin` is for FRONTEND DISPLAY ONLY (showing the admin tab). It is
    # NOT authority — backend admin access is gated by require_admin() in deps.py,
    # which re-checks email == settings.admin_email and ignores this claim. Never
    # read payload["is_admin"] as an authorization signal.
    return jwt.encode(
        {"sub": str(user_id), "email": email, "is_admin": is_admin,
         "tv": token_version, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _cookie_secure() -> bool:
    app_url = (settings.app_url or "").lower()
    return not app_url.startswith(("http://localhost", "http://127.0.0.1", "http://test"))


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=_cookie_secure(),
        samesite="lax",
    )


def _session_response(user: User) -> SessionResponse:
    return SessionResponse(
        email=user.email,
        is_admin=bool(settings.admin_email and user.email == settings.admin_email),
        onboarding_role=user.onboarding_role,
        onboarding_video_use=user.onboarding_video_use,
        onboarding_note=user.onboarding_note,
        company_context=user.company_context,
        product_context=user.product_context,
        reference_urls=user.reference_urls,
    )


@router.post("/register")
@limiter.limit("5/hour")
async def register(request: Request, req: AuthRequest, session: AsyncSession = Depends(get_session)):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Пароль должен быть не менее 8 символов")
    # Email is case-insensitive: store/look up lowercased so a user who registered
    # as "Ivan@mail.ru" (mobile keyboards auto-capitalize) can log in as "ivan@mail.ru".
    email = req.email.strip().lower()
    if not _is_allowed_registration_email(email):
        raise HTTPException(status_code=400, detail=RU_EMAIL_MESSAGE)
    existing = await session.scalar(select(User).where(func.lower(User.email) == email))

    # Registrations closed → record to the waitlist, no verification email. The
    # admin approves later (→ invite email). We never reveal whether the email was
    # already known: every call returns the same "waitlisted" response.
    if not await registration_open(session):
        if not existing:
            user = User(
                email=email,
                hashed_password=await _hash_async(req.password),
                waitlisted=True,
            )
            _apply_onboarding_context(user, req)
            session.add(user)
            await session.commit()
            return {"status": "waitlisted"}

    if existing:
        # Don't reveal whether an email is registered — same response as success.
        # Unverified user re-registering: refresh the token and resend the email
        # (covers "first email never arrived" without enabling enumeration).
        if existing.email_verified:
            return {"status": "verify_email_sent"}
        if not existing.email_verified:
            # Throttle resends: escalating cooldown, then a hard stop. The block
            # message is shown to the user (this path does reveal an unverified
            # account exists — accepted trade-off for clear resend feedback).
            block = _verification_block_message(existing)
            if block:
                raise HTTPException(status_code=429, detail=block)
            new_token = secrets.token_urlsafe(32)
        existing.verification_token = new_token
        existing.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        existing.hashed_password = await _hash_async(req.password)
        _apply_onboarding_context(existing, req)
        _record_verification_send(existing)
        await session.commit()
        _fire_and_forget(send_verification_email(email, new_token), "verification_email")
        _fire_and_forget(send_onboarding_email(email, req.role, req.video_use, req.onboarding_note), "onboarding_email")
        return {"status": "verify_email_sent"}
    token = secrets.token_urlsafe(32)
    user = User(
        email=email,
        hashed_password=await _hash_async(req.password),
        verification_token=token,
        verification_token_expires=datetime.utcnow() + timedelta(hours=24),
    )
    _apply_onboarding_context(user, req)
    session.add(user)
    _record_verification_send(user)  # first send → count=1, starts the cooldown chain
    await session.commit()
    _fire_and_forget(send_verification_email(email, token), "verification_email")
    _fire_and_forget(send_onboarding_email(email, req.role, req.video_use, req.onboarding_note), "onboarding_email")
    return {"status": "verify_email_sent"}


@router.post("/login", response_model=SessionResponse)
@limiter.limit("10/minute")
async def login(response: Response, request: Request, req: AuthRequest, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(func.lower(User.email) == req.email.strip().lower()))
    if not user or not await _verify_async(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="email_not_verified")
    _set_session_cookie(response, _make_token(user.id, user.email, token_version=user.token_version))
    return _session_response(user)


@router.get("/verify-email", response_model=SessionResponse)
@limiter.limit("30/hour")
async def verify_email(response: Response, request: Request, token: str, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.verification_token == token))
    if not user:
        raise HTTPException(status_code=400, detail="Неверная или истёкшая ссылка")
    if user.verification_token_expires and user.verification_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Ссылка истекла — зарегистрируйтесь заново")
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    await session.commit()
    _set_session_cookie(response, _make_token(user.id, user.email, token_version=user.token_version))
    return _session_response(user)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(max_length=254)


@router.post("/forgot-password")
@limiter.limit("5/hour")
async def forgot_password(request: Request, req: ForgotPasswordRequest, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(func.lower(User.email) == req.email.strip().lower()))
    if user and user.email_verified:
        # Same escalating throttle as verification (10→30→60 min, then a hard
        # stop → support). Counter is cleared on a successful reset below, so a
        # user who genuinely forgets their password again later isn't locked out.
        block = _reset_block_message(user)
        if block:
            raise HTTPException(status_code=429, detail=block)
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        _record_reset_send(user)
        await session.commit()
        _fire_and_forget(send_reset_email(user.email, token), "reset_email")
    return {"status": "reset_email_sent"}


class ResetPasswordRequest(BaseModel):
    token: str = Field(max_length=100)
    new_password: str = Field(max_length=128)


@router.post("/reset-password")
@limiter.limit("10/hour")
async def reset_password(request: Request, req: ResetPasswordRequest, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.reset_token == req.token))
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Неверная или истёкшая ссылка")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Пароль должен быть не менее 8 символов")
    user.hashed_password = await _hash_async(req.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.token_version += 1  # invalidate any sessions opened before the reset
    user.reset_send_count = 0  # clear the throttle so future resets aren't capped
    user.reset_last_sent = None
    await session.commit()
    return {"ok": True}


class MeResponse(BaseModel):
    email: str
    is_admin: bool


@router.get("/me", response_model=MeResponse)
async def get_me(user: User = Depends(get_current_user)):
    return MeResponse(
        email=user.email,
        is_admin=bool(settings.admin_email and user.email == settings.admin_email),
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


class ChangePasswordResponse(BaseModel):
    ok: bool = True


@router.put("/me/password", response_model=ChangePasswordResponse)
@limiter.limit("10/hour")
async def change_password(
    response: Response,
    request: Request,
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user.id)
    if not await _verify_async(req.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Новый пароль должен быть не менее 8 символов")
    user.hashed_password = await _hash_async(req.new_password)
    user.token_version += 1  # kill all other sessions; reissue for this one below
    await session.commit()
    _set_session_cookie(response, _make_token(user.id, user.email, token_version=user.token_version))
    return ChangePasswordResponse()


@router.post("/logout", response_model=OkResponse)
async def logout(response: Response):
    _clear_session_cookie(response)
    return OkResponse()
