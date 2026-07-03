import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sa_delete

from ..db import get_session
from ..models import SystemPrompt, AppSetting, User, ErrorLog
from ..schemas import SystemPromptOut, SystemPromptUpdate, AppSettingOut, AppSettingUpdate
from ..config import settings
from ..deps import require_admin
from ..email import send_invite_email

router = APIRouter()


@router.get("/prompts", response_model=list[SystemPromptOut])
async def list_prompts(
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(SystemPrompt).order_by(SystemPrompt.key))
    return result.scalars().all()


@router.put("/prompts/{key}", response_model=SystemPromptOut)
async def update_prompt(
    key: str,
    body: SystemPromptUpdate,
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    prompt = await session.get(SystemPrompt, key)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    prompt.content = body.content
    await session.commit()
    await session.refresh(prompt)
    return prompt


@router.get("/settings", response_model=list[AppSettingOut])
async def list_settings(
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(AppSetting).order_by(AppSetting.key))
    return result.scalars().all()


@router.put("/settings/{key}", response_model=AppSettingOut)
async def update_setting(
    key: str,
    body: AppSettingUpdate,
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    setting = await session.get(AppSetting, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    setting.value = body.value
    await session.commit()
    await session.refresh(setting)
    return setting


# ── Users ────────────────────────────────────────────────────────────────────

USERS_PAGE_SIZE = 10


@router.get("/users")
async def list_users(
    email: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    base = select(User)
    if email:
        base = base.where(User.email.ilike(f"%{email}%"))
    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    result = await session.execute(
        base.order_by(User.created_at.desc())
        .offset((page - 1) * USERS_PAGE_SIZE)
        .limit(USERS_PAGE_SIZE)
    )
    users = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": USERS_PAGE_SIZE,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "email_verified": u.email_verified,
                "waitlisted": u.waitlisted,
                "created_at": u.created_at,
            }
            for u in users
        ],
    }


class VerifyUserBody(BaseModel):
    email: str


@router.post("/users/reset-link")
async def create_reset_link(
    body: VerifyUserBody,
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = await session.scalar(select(User).where(func.lower(User.email) == body.email.strip().lower()))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    await session.commit()
    return {"email": user.email, "reset_url": f"{settings.app_url}/reset-password?token={token}"}


@router.post("/users/verify")
async def verify_user(
    body: VerifyUserBody,
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = await session.scalar(select(User).where(func.lower(User.email) == body.email.strip().lower()))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    await session.commit()
    return {"email": user.email, "email_verified": True}


@router.post("/users/approve")
async def approve_user(
    body: VerifyUserBody,
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Approve a waitlisted sign-up: clear the waitlist flag and email them an
    invite (verification link). They confirm and can then log in."""
    user = await session.scalar(select(User).where(func.lower(User.email) == body.email.strip().lower()))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    token = secrets.token_urlsafe(32)
    user.waitlisted = False
    user.verification_token = token
    user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    await session.commit()
    asyncio.create_task(send_invite_email(user.email, token))
    return {"email": user.email, "waitlisted": False, "invited": True}


# ── Errors ───────────────────────────────────────────────────────────────────

class ErrorLogOut(BaseModel):
    id: int
    created_at: datetime
    method: str
    path: str
    status: int
    kind: str
    message: str
    traceback: str

    class Config:
        from_attributes = True


@router.get("/errors", response_model=list[ErrorLogOut])
async def list_errors(
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
):
    rows = await session.scalars(
        select(ErrorLog).order_by(ErrorLog.created_at.desc()).limit(limit)
    )
    return list(rows)


@router.delete("/errors", status_code=204)
async def clear_errors(
    _=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(sa_delete(ErrorLog))
    await session.commit()


# ── Seed ─────────────────────────────────────────────────────────────────────
# ponytail: source project seeded fake Generation rows for UI testing; that model
# doesn't exist in this base template. Reinterpreted as "re-run the idempotent
# startup seed" (useful after editing a prompts/*.txt file without a redeploy).

@router.post("/seed", status_code=201)
async def reseed(_=Depends(require_admin)):
    from ..main import _seed_prompts, _seed_settings
    await _seed_prompts()
    await _seed_settings()
    return {"ok": True}
