import asyncio
import logging
import os
import traceback as _traceback
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .limiter import limiter
from .release import release_info

logger = logging.getLogger("{{PROJECT_SLUG}}")

# Generic user-facing message — never leak a traceback or library text.
_GENERIC_ERROR = "Что-то пошло не так. Мы уже знаем о проблеме, попробуйте позже."


# --- Access-log noise filter ------------------------------------------------
# Bots/scanners hammer the API with 404s on paths we don't serve (/gsi, /.env,
# /admin.php, …). Those drown the real logs. Drop access-log lines for 404s on
# paths outside our known route prefixes; genuine in-API 404s still log.
_KNOWN_PREFIXES = (
    "/auth", "/tracking", "/admin", "/storage", "/health", "/docs", "/redoc", "/openapi.json",
)


class _ScannerNoiseFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        # uvicorn.access args: (client_addr, method, full_path, http_ver, status)
        if isinstance(args, tuple) and len(args) >= 5:
            try:
                status = int(args[4])
                path = str(args[2])
            except (ValueError, TypeError):
                return True
            if status == 404 and not path.startswith(_KNOWN_PREFIXES):
                return False  # scanner probe — drop
        return True


logging.getLogger("uvicorn.access").addFilter(_ScannerNoiseFilter())

from sqlalchemy import select
from .config import settings
from .db import create_tables, SessionLocal
from .deps import SESSION_COOKIE_NAME
from .routers import auth, tracking, admin as admin_router

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# ponytail: one example key so the seeding mechanism has something to seed.
# Add real keys here as the product grows; each needs a matching
# prompts/<key>.txt file (see _read_prompt_file).
_PROMPT_KEYS = [
    ("example/system", "Example — system prompt"),
]


def _read_prompt_file(key: str) -> str:
    f = PROMPTS_DIR / f"{key}.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else ""


async def _seed_prompts() -> None:
    from .models import SystemPrompt
    try:
        async with SessionLocal() as session:
            for key, label in _PROMPT_KEYS:
                content = _read_prompt_file(key)
                existing = await session.get(SystemPrompt, key)
                if existing:
                    existing.label = label
                    existing.content = content
                else:
                    session.add(SystemPrompt(key=key, label=label, content=content))
            await session.commit()
    except Exception as exc:
        print(f"[seed_prompts] FAILED: {exc}", flush=True)


async def _seed_settings() -> None:
    from .models import AppSetting
    try:
        async with SessionLocal() as session:
            # Registrations open by default. When "0", sign-ups go to a waitlist
            # (no verification email) until the admin approves them.
            if not await session.get(AppSetting, "registration_open"):
                session.add(AppSetting(key="registration_open", value="1"))
            await session.commit()
    except Exception as exc:
        print(f"[seed_settings] FAILED: {exc}", flush=True)


async def _seed_users() -> None:
    from .models import User
    from .routers.auth import _hash

    if not (settings.admin_email and settings.admin_password):
        return

    try:
        async with SessionLocal() as session:
            existing = await session.scalar(select(User).where(User.email == settings.admin_email))
            if not existing:
                session.add(User(email=settings.admin_email, hashed_password=_hash(settings.admin_password), email_verified=True))
                await session.commit()
                print(f"[seed] created admin {settings.admin_email}", flush=True)
            elif not existing.email_verified:
                # Admin was registered manually (unverified) before the seed ran,
                # and prod mail may be down → self-heal so the admin can log in.
                existing.email_verified = True
                await session.commit()
                print(f"[seed] verified existing admin {settings.admin_email}", flush=True)
            else:
                print("[seed] admin already exists, skipping", flush=True)
        print("[seed] done", flush=True)
    except Exception as exc:
        print(f"[seed] FAILED: {exc}", flush=True)


async def _clear_maintenance() -> None:
    # The deploy script sets maintenance=1 before stopping containers; a fresh
    # API start means the new code is live, so lift the block automatically.
    import redis.asyncio as aioredis
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.delete("maintenance")
        await r.aclose()
    except Exception as exc:
        print(f"[clear_maintenance] FAILED: {exc}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .backup import backup_loop
    if settings.jwt_secret == "changeme":
        raise RuntimeError(
            "JWT_SECRET is not configured (.env missing or not loaded) — refusing to start"
        )
    await create_tables()
    await _seed_prompts()
    await _seed_settings()
    await _seed_users()
    await _clear_maintenance()
    task = asyncio.create_task(backup_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="{{PROJECT_NAME}} API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 50 MB request cap — protects memory until a reverse proxy fronts the API.
_MAX_BODY = 50 * 1024 * 1024


@app.middleware("http")
async def limit_body_size(request, call_next):
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > _MAX_BODY:
        return JSONResponse(status_code=413, content={"detail": "Запрос слишком большой"})
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    return response

_app_origin = settings.app_url.rstrip("/")
_cors_origins = [_app_origin]
if "localhost" not in settings.app_url:
    # Allow the www. variant too (covers users hitting www before any redirect)
    if "://" in _app_origin and "://www." not in _app_origin:
        scheme, host = _app_origin.split("://", 1)
        _cors_origins.append(f"{scheme}://www.{host}")
    _cors_origins += ["http://localhost:3000", "http://localhost:3001"]  # dev access


def _request_origin(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if not referer:
        return None
    parsed = urlparse(referer)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return None


@app.middleware("http")
async def csrf_origin_check(request: Request, call_next):
    # Cookie auth makes browser-sent mutating requests ambient. SameSite=Lax blocks
    # normal cross-site POSTs; this rejects anything that still arrives with our
    # session cookie from an unexpected Origin/Referer.
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.cookies.get(SESSION_COOKIE_NAME)
    ):
        origin = _request_origin(request)
        if origin not in _cors_origins:
            return JSONResponse(status_code=403, content={"detail": "Недопустимый источник запроса"})
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

os.makedirs(settings.storage_path, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.storage_path), name="storage")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tracking.router, prefix="/tracking", tags=["tracking"])
app.include_router(admin_router.router, prefix="/admin", tags=["admin"])


async def _record_error(request: Request, exc: Exception, status: int) -> None:
    """Best-effort: persist the failure so the admin sees it. Never raises.
    Stores only metadata + traceback — NOT the request body (base64/passwords)."""
    from .db import SessionLocal
    from .models import ErrorLog
    try:
        tb = "".join(_traceback.format_exception(type(exc), exc, exc.__traceback__))
        async with SessionLocal() as session:
            session.add(ErrorLog(
                method=request.method[:10],
                path=str(request.url.path)[:300],
                status=status,
                kind=type(exc).__name__[:160],
                message=str(exc)[:2000],
                traceback=tb[:8000],
            ))
            await session.commit()
    except Exception:
        logger.error("Failed to persist error log", exc_info=True)
    # Pluggable alert channel — off until prod mail is live.
    if getattr(settings, "error_email_alerts", False):
        with suppress(Exception):
            from .email import send_error_alert
            asyncio.create_task(send_error_alert(
                f"{request.method} {request.url.path}", type(exc).__name__, str(exc)[:500]
            ))


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    # Pydantic spits out a scary array — give the user one clean line.
    return JSONResponse(status_code=422, content={"detail": "Проверьте введённые данные."})


@app.exception_handler(Exception)
async def _unhandled_handler(request: Request, exc: Exception):
    # Only truly unhandled errors reach here — HTTPException keeps its own
    # (friendly) detail and is handled by FastAPI before this.
    logger.error("Unhandled error: %s %s", request.method, request.url.path, exc_info=True)
    await _record_error(request, exc, 500)
    return JSONResponse(status_code=500, content={"detail": _GENERIC_ERROR})


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/version")
async def version():
    return release_info()


@app.get("/health/version")
async def health_version():
    return release_info()
