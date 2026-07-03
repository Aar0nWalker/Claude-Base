from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import User, UserActionEvent

router = APIRouter()


class TrackEventIn(BaseModel):
    event: str = Field(max_length=80)
    path: str = Field("", max_length=500)
    target: Optional[str] = Field(None, max_length=200)
    label: Optional[str] = Field(None, max_length=300)
    session_id: Optional[str] = Field(None, max_length=80)
    meta: dict = Field(default_factory=dict)


def _safe_meta(value: dict) -> dict:
    out: dict[str, str | int | float | bool | None] = {}
    for key, raw in (value or {}).items():
        if len(out) >= 20:
            break
        k = str(key)[:80]
        if isinstance(raw, (str, int, float, bool)) or raw is None:
            out[k] = raw if not isinstance(raw, str) else raw[:500]
        else:
            out[k] = str(raw)[:500]
    return out


@router.post("/events", status_code=204)
async def track_event(
    body: TrackEventIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    session.add(UserActionEvent(
        user_id=current_user.id,
        session_id=(body.session_id or "").strip()[:80] or None,
        event=(body.event or "event").strip()[:80],
        path=(body.path or str(request.url.path)).strip()[:500],
        target=(body.target or "").strip()[:200] or None,
        label=(body.label or "").strip()[:300] or None,
        meta=_safe_meta(body.meta),
        created_at=datetime.utcnow(),
    ))
    await session.commit()
