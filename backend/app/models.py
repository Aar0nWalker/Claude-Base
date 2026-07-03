from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    verification_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Verification-email throttle: count of emails sent + when the last one went
    # out. Escalating cooldown (10→30→60 min); after 3 sends the user is told to
    # contact support. See auth._verification_block_message.
    verification_send_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_last_sent: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reset_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Password-reset email throttle (same 10→30→60 escalation as verification).
    # Cleared on a successful reset so repeat forgetfulness isn't permanently capped.
    reset_send_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reset_last_sent: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Bumped on password change/reset → all tokens issued with an older value are
    # rejected (kills existing sessions). See deps.get_current_user.
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    onboarding_role: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    onboarding_video_use: Mapped[Optional[str]] = mapped_column(String(800), nullable=True)
    onboarding_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_urls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # True when the account was created while registrations were CLOSED — recorded
    # to a waitlist, no verification email sent. Admin approves (→ invite email,
    # flag cleared) to let them in. See auth.register / admin.approve_user.
    waitlisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SystemPrompt(Base):
    __tablename__ = "system_prompts"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False, default="")


class ErrorLog(Base):
    """Server-side error log — written by the global exception handler so the
    admin sees failures without the user ever getting a raw traceback.
    Never store request bodies here (they carry base64 media / passwords)."""
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    path: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    kind: Mapped[str] = mapped_column(String(160), nullable=False, default="")   # exception class
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    traceback: Mapped[str] = mapped_column(Text, nullable=False, default="")
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class UserActionEvent(Base):
    """Append-only product analytics event captured from the authenticated app."""

    __tablename__ = "user_action_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False, default="", index=True)
    target: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class PendingMediaDelete(Base):
    """Media object that should be deleted from storage after a transient failure."""

    __tablename__ = "pending_media_deletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
