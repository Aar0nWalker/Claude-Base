import os

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_session
from .models import User, AppSetting

# ponytail: plain valid cookie name so the raw template runs out of the box.
# Override via env if you host multiple apps on one domain.
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "session")
_bearer = HTTPBearer(auto_error=False)


def _token_from_request(request: Request, creds: HTTPAuthorizationCredentials | None) -> str | None:
    return request.cookies.get(SESSION_COOKIE_NAME) or (creds.credentials if creds else None)


async def _user_from_token(token: str | None, session: AsyncSession) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # Session invalidation: a token minted before the last password change/reset
    # carries an older token_version and is no longer valid.
    if payload.get("tv", 0) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return user


async def require_admin(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await _user_from_token(_token_from_request(request, creds), session)
    # Verify admin against current config, not the token claim — a stale token
    # must not keep admin rights after ADMIN_EMAIL changes
    if not (settings.admin_email and user.email == settings.admin_email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только для администраторов")
    return user


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    return await _user_from_token(_token_from_request(request, creds), session)


async def registration_open(session: AsyncSession) -> bool:
    """Open by default — closed only when the admin sets registration_open="0".
    When closed, sign-ups are waitlisted instead of emailed a verification link."""
    setting = await session.get(AppSetting, "registration_open")
    return setting is None or setting.value != "0"
