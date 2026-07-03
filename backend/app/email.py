import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

import aiosmtplib

from .config import settings

logger = logging.getLogger(__name__)


async def _send(to: str, subject: str, html: str, text: str) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        logger.info("[email] SMTP not configured — skipping: %s → %s", subject, to)
        return
    # SMTP login may be an API-key ID rather than an address — the visible sender
    # is MAIL_FROM (must be on a domain verified with the SMTP provider).
    sender = settings.mail_from or settings.smtp_user
    sender_domain = sender.split("@")[-1] if "@" in sender else settings.app_url.split("://")[-1].split("/")[0]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{{PROJECT_NAME}} <{sender}>"
    msg["To"] = to
    # Standard headers — their absence is a top spam-filter trigger
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender_domain)
    # Plain-text part first, then HTML: HTML-only mail scores as spam
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )


async def send_verification_email(to: str, token: str) -> None:
    url = f"{settings.app_url}/verify-email?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#111">Подтвердите email</h2>
      <p>Добро пожаловать в <strong>{{PROJECT_NAME}}</strong>! Нажмите кнопку ниже, чтобы подтвердить адрес.</p>
      <a href="{url}" style="display:inline-block;padding:12px 24px;background:#6c47ff;color:#fff;border-radius:8px;text-decoration:none;font-weight:600">
        Подтвердить email
      </a>
      <p style="color:#888;font-size:13px;margin-top:20px">Ссылка действует 24 часа. Если вы не регистрировались — проигнорируйте письмо.</p>
    </div>
    """
    text = (
        "Добро пожаловать в {{PROJECT_NAME}}!\n\n"
        f"Подтвердите свой email, перейдя по ссылке:\n{url}\n\n"
        "Ссылка действует 24 часа. Если вы не регистрировались — проигнорируйте это письмо."
    )
    try:
        await _send(to, "Подтвердите email — {{PROJECT_NAME}}", html, text)
    except Exception:
        logger.warning("[email] failed to send verification to %s", to, exc_info=True)


async def send_invite_email(to: str, token: str) -> None:
    """Sent when the admin approves a waitlisted sign-up — the "next batch" invite.
    Same verification link, friendlier 'you're in' copy."""
    url = f"{settings.app_url}/verify-email?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#111">Доступ открыт</h2>
      <p>Мы открыли вам доступ в <strong>{{PROJECT_NAME}}</strong>! Подтвердите email и заходите.</p>
      <a href="{url}" style="display:inline-block;padding:12px 24px;background:#6c47ff;color:#fff;border-radius:8px;text-decoration:none;font-weight:600">
        Подтвердить email и войти
      </a>
      <p style="color:#888;font-size:13px;margin-top:20px">Ссылка действует 24 часа.</p>
    </div>
    """
    text = (
        "Доступ в {{PROJECT_NAME}} открыт!\n\n"
        f"Подтвердите email и заходите:\n{url}\n\n"
        "Ссылка действует 24 часа."
    )
    try:
        await _send(to, "Доступ в {{PROJECT_NAME}} открыт — подтвердите email", html, text)
    except Exception:
        logger.warning("[email] failed to send invite to %s", to, exc_info=True)


async def send_onboarding_email(
    user_email: str,
    role: str | None,
    video_use: str | None,
    extra: str | None,
) -> None:
    to = settings.admin_email
    if not to:
        return
    role = (role or "Не указано").strip()
    video_use = (video_use or "Не указано").strip()
    extra = (extra or "Не указано").strip()
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:0 auto">
      <h2 style="color:#111">Новая регистрация {{PROJECT_NAME}}</h2>
      <p><strong>Email:</strong> {user_email}</p>
      <p><strong>Роль:</strong> {role}</p>
      <p><strong>Где планирует использовать сервис:</strong><br>{video_use}</p>
      <p><strong>Комментарий:</strong><br>{extra}</p>
    </div>
    """
    text = (
        "Новая регистрация {{PROJECT_NAME}}\n\n"
        f"Email: {user_email}\n"
        f"Роль: {role}\n"
        f"Использование: {video_use}\n"
        f"Комментарий: {extra}"
    )
    try:
        await _send(to, f"Новая регистрация {{PROJECT_NAME}}: {user_email}", html, text)
    except Exception:
        logger.warning("[email] failed to send onboarding answers for %s", user_email, exc_info=True)


async def send_error_alert(where: str, kind: str, message: str) -> None:
    """Notify the admin of an unhandled error. Best-effort; gated by
    settings.error_email_alerts in the caller. Recipient = ADMIN_EMAIL."""
    to = settings.admin_email
    if not to:
        return
    html = (
        '<div style="font-family:sans-serif;max-width:520px;margin:0 auto">'
        '<h3 style="color:#c0392b">Ошибка на сервере {{PROJECT_NAME}}</h3>'
        f"<p><strong>{kind}</strong></p>"
        f"<p style=\"color:#555\">{where}</p>"
        f'<pre style="background:#f5f5f5;padding:12px;border-radius:8px;white-space:pre-wrap">{message}</pre>'
        "</div>"
    )
    text = f"Ошибка {{PROJECT_NAME}}\n{kind}\n{where}\n\n{message}"
    try:
        await _send(to, f"⚠️ Ошибка {{PROJECT_NAME}}: {kind}", html, text)
    except Exception:
        logger.warning("[email] failed to send error alert", exc_info=True)


async def send_reset_email(to: str, token: str) -> None:
    url = f"{settings.app_url}/reset-password?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#111">Сброс пароля</h2>
      <p>Вы запросили сброс пароля в <strong>{{PROJECT_NAME}}</strong>. Нажмите кнопку ниже.</p>
      <a href="{url}" style="display:inline-block;padding:12px 24px;background:#6c47ff;color:#fff;border-radius:8px;text-decoration:none;font-weight:600">
        Сбросить пароль
      </a>
      <p style="color:#888;font-size:13px;margin-top:20px">Ссылка действует 1 час. Если вы не запрашивали сброс — проигнорируйте письмо.</p>
    </div>
    """
    text = (
        "Вы запросили сброс пароля в {{PROJECT_NAME}}.\n\n"
        f"Перейдите по ссылке, чтобы задать новый пароль:\n{url}\n\n"
        "Ссылка действует 1 час. Если вы не запрашивали сброс — проигнорируйте это письмо."
    )
    try:
        await _send(to, "Сброс пароля — {{PROJECT_NAME}}", html, text)
    except Exception:
        logger.warning("[email] failed to send reset to %s", to, exc_info=True)
