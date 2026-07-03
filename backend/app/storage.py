"""Object storage (S3-compatible) with a local fallback.

If S3 is not configured (env empty), files stay on the local `/storage` volume and
are served via the `/backend` proxy + StaticFiles mount — exactly as before. Once
S3 env is filled, generated media is uploaded and the local copy removed; the URL
stored in the DB becomes the full public CDN/bucket URL.
"""
import logging
import os
import uuid
from typing import Optional
from urllib.parse import urlparse

import aioboto3

from .config import settings

logger = logging.getLogger(__name__)
MAX_PUBLIC_MEDIA_DOWNLOAD_BYTES = 120 * 1024 * 1024

_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def s3_enabled() -> bool:
    return bool(
        settings.s3_endpoint
        and settings.s3_bucket
        and settings.s3_key_id
        and settings.s3_key_secret
    )


def _public_base() -> str:
    base = settings.cdn_base or f"{settings.s3_endpoint}/{settings.s3_bucket}"
    return base.rstrip("/")


async def _upload(local_path: str, key: str) -> str:
    ext = os.path.splitext(local_path)[1].lower()
    content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        region_name=settings.s3_region or None,
        aws_access_key_id=settings.s3_key_id,
        aws_secret_access_key=settings.s3_key_secret,
    ) as s3:
        await s3.upload_file(
            local_path, settings.s3_bucket, key,
            ExtraArgs={"ContentType": content_type},
        )
    return f"{_public_base()}/{key}"


async def store_file(local_path: str, key: str, local_url: str) -> str:
    """Upload to S3 and drop the local copy; return the public URL.

    `local_url` is returned unchanged when S3 is off, or when the upload fails
    (the local file is kept so nothing is lost). Callers store the returned URL.
    """
    if not s3_enabled():
        return local_url
    try:
        url = await _upload(local_path, key)
    except Exception:
        logger.error("S3 upload failed for %s — keeping local file", key, exc_info=True)
        return local_url
    try:
        os.remove(local_path)
    except OSError:
        pass
    return url


def _key_from_url(file_url: str) -> Optional[str]:
    """Recover the S3 object key from a stored URL. Handles both the current
    CDN_BASE prefix and the legacy raw `endpoint/bucket` form (pre-migration)."""
    base = _public_base()
    if file_url.startswith(base):
        return file_url[len(base):].lstrip("/")
    raw = f"{settings.s3_endpoint.rstrip('/')}/{settings.s3_bucket}"
    if settings.s3_endpoint and settings.s3_bucket and file_url.startswith(raw):
        return file_url[len(raw):].lstrip("/")
    return None


def is_managed_media_url(file_url: Optional[str]) -> bool:
    """True for media owned by this app: local `/storage/...` or configured S3/CDN.

    External URLs can share a basename with local files. Treating every URL
    basename as local media would let cleanup delete the wrong object.
    """
    if not file_url:
        return False
    if file_url.startswith("/storage/"):
        return True
    return _key_from_url(file_url) is not None


async def download_media(file_url: str, dst: str) -> bool:
    """Download an S3-stored object to `dst`. Returns False if S3 is off or the
    object can't be located/fetched (caller falls back / errors)."""
    if not s3_enabled():
        return False
    key = _key_from_url(file_url)
    if not key:
        return False
    try:
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region or None,
            aws_access_key_id=settings.s3_key_id,
            aws_secret_access_key=settings.s3_key_secret,
        ) as s3:
            await s3.download_file(settings.s3_bucket, key, dst)
        return True
    except Exception:
        logger.error("S3 download failed for %s", file_url, exc_info=True)
        return False


async def download_public_media(file_url: str, dst: str) -> bool:
    """Best-effort fallback for public CDN/media URLs.

    S3 is preferred because it uses object keys directly. This path handles legacy
    rows where the DB stores a public `/media/...` URL that is still reachable but
    no longer maps cleanly to the current S3/CDN base.
    """
    if not file_url.startswith(("http://", "https://")):
        return False
    allowed_prefixes = [_public_base()]
    if settings.s3_endpoint and settings.s3_bucket:
        allowed_prefixes.append(f"{settings.s3_endpoint.rstrip('/')}/{settings.s3_bucket}")
    parsed = urlparse(file_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    if not any(file_url.startswith(prefix.rstrip("/") + "/") or file_url == prefix.rstrip("/") for prefix in allowed_prefixes if prefix):
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            async with client.stream("GET", file_url) as resp:
                if resp.status_code != 200:
                    return False
                size = 0
                with open(dst, "wb") as f:
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            size += len(chunk)
                            if size > MAX_PUBLIC_MEDIA_DOWNLOAD_BYTES:
                                logger.warning("public media download too large: %s", file_url)
                                try:
                                    os.remove(dst)
                                except OSError:
                                    pass
                                return False
                            f.write(chunk)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            return True
    except Exception:
        logger.error("public media download failed for %s", file_url, exc_info=True)
    try:
        if os.path.exists(dst):
            os.remove(dst)
    except OSError:
        pass
    return False


async def ensure_local_media(file_url: str, storage_path: str) -> tuple[Optional[str], bool]:
    """Guarantee a local copy for local processing. Returns (path, is_temp):
    uses the existing local file if present (is_temp=False); otherwise pulls the
    object down from S3 into a temp file (is_temp=True → caller must delete it).
    Returns (None, False) when the file can't be found anywhere."""
    local = os.path.join(storage_path, os.path.basename(file_url))
    if os.path.exists(local):
        return local, False
    if not s3_enabled():
        return None, False
    ext = os.path.splitext(file_url)[1] or ".bin"
    tmp = os.path.join(storage_path, f"_src_{uuid.uuid4().hex}{ext}")
    if await download_media(file_url, tmp):
        return tmp, True
    if await download_public_media(file_url, tmp):
        return tmp, True
    return None, False


async def delete_media(file_url: Optional[str], storage_path: str) -> bool:
    """Best-effort removal of stored media. Returns False when cleanup should be retried."""
    if not file_url:
        return True

    ok = await delete_key(file_url)
    if not is_managed_media_url(file_url):
        return ok

    local = os.path.join(storage_path, os.path.basename(file_url))
    if os.path.exists(local):
        try:
            os.remove(local)
        except OSError:
            logger.warning("local media delete failed %s", local, exc_info=True)
            ok = False
    return ok


async def delete_key(file_url: str) -> bool:
    """Best-effort delete object by stored URL. Returns False when S3 should be retried."""
    if not s3_enabled():
        return True
    # Handles both current CDN_BASE prefix and legacy raw endpoint/bucket URLs
    # (pre-migration), so old objects don't get orphaned in bucket on delete.
    key = _key_from_url(file_url)
    if not key:
        return True
    try:
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region or None,
            aws_access_key_id=settings.s3_key_id,
            aws_secret_access_key=settings.s3_key_secret,
        ) as s3:
            await s3.delete_object(Bucket=settings.s3_bucket, Key=key)
        return True
    except Exception:
        logger.warning("S3 delete failed %s", file_url, exc_info=True)
        return False
