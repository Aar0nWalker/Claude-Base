from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    storage_path: str = "/storage"
    database_url: str = "postgresql+asyncpg://{{PROJECT_SLUG}}:{{PROJECT_SLUG}}@db:5432/{{PROJECT_SLUG}}"
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    admin_email: str = ""
    admin_password: str = ""
    # Transactional email via SMTP (any provider).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = ""       # visible sender, e.g. no-reply@{{DOMAIN}}
    # Public support address shown to users (e.g. when they hit the verification
    # resend limit). Falls back to mail_from at use-site if empty.
    support_email: str = ""
    app_url: str = "http://localhost:3000"
    # Backend's own public base URL, used for building absolute links back to
    # the API itself (e.g. media URLs) when not proxied behind app_url.
    backend_url: str = "http://localhost:8000"
    # S3-compatible object storage. Empty → media stays on the local volume.
    s3_endpoint: str = ""
    s3_region: str = ""
    s3_bucket: str = ""
    s3_key_id: str = ""
    s3_key_secret: str = ""
    cdn_base: str = ""        # public base URL; empty → endpoint/bucket
    # Email the admin on unhandled errors. Off until prod mail is live; errors
    # are always written to the DB error log regardless of this flag.
    error_email_alerts: bool = False
    # Anthropic / Claude — optional text helper (see ai_text.py). Empty key →
    # disabled. Read from env ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL.
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    anthropic_model: str = "claude-opus-4-8"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
