from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import jwt, JWTError

from .config import settings
from .deps import SESSION_COOKIE_NAME


def _user_or_ip(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    if token:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                # verify_exp=False on purpose: rate-limit keying only. An expired
                # token should still key to its user (not fall back to shared IP)
                # so quota isn't bypassed by letting a token lapse. Auth itself is
                # enforced separately in deps.get_current_user, which does check exp.
                options={"verify_exp": False},
            )
            return f"u:{payload.get('sub', '')}"
        except (JWTError, KeyError, ValueError):
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_user_or_ip)
