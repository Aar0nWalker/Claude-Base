ARG PYTHON_IMAGE=mirror.gcr.io/library/python:3.12-slim
FROM ${PYTHON_IMAGE}

WORKDIR /app

# Keep apt's downloaded .debs (Debian images delete them by default) so the
# BuildKit cache mount below can reuse them across builds — no re-download.
RUN rm -f /etc/apt/apt.conf.d/docker-clean \
    && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# postgresql-client for pg_dump (see app/backup.py). Cache mounts persist the
# apt lists + downloaded debs between builds, so a layer rebuild (or a flaky
# network) doesn't re-fetch packages every time.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client

COPY requirements.txt .
# Resilient install: PyPI/files.pythonhosted.org can be flaky from the server, so
# give pip a long read timeout + many retries. The pip cache mount keeps already
# downloaded wheels between builds → no re-download even if this layer rebuilds.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 180 --retries 15 -r requirements.txt

COPY . .
# Tests run before deploy via backend/Dockerfile.test. Dev test files are not
# shipped to the server or installed in the prod image.

RUN groupadd --system app && useradd --system --gid app app \
    && mkdir -p /storage /backups \
    && chown -R app:app /storage /backups /app

USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
