"""Email sending service using fastapi-mail with Gmail SMTP"""
import logging
from pathlib import Path
from typing import Optional

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

TEMPLATE_DIR = Path(__file__).parent / "templates"


def get_mail_config() -> ConnectionConfig:
    """Create fastapi-mail connection config from app settings."""
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM or settings.MAIL_USERNAME,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=TEMPLATE_DIR,
    )


_fast_mail: Optional[FastMail] = None


def get_fast_mail() -> FastMail:
    """Get cached FastMail instance."""
    global _fast_mail
    if _fast_mail is None:
        _fast_mail = FastMail(get_mail_config())
    return _fast_mail


async def send_email(
    recipients: list[str],
    subject: str,
    template_name: str,
    template_body: dict,
) -> bool:
    """Send an email using a Jinja2 HTML template.

    Args:
        recipients: List of email addresses.
        subject: Email subject line.
        template_name: Name of the template file in templates/ dir (e.g. "welcome.html").
        template_body: Dict of variables passed to the Jinja2 template.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not settings.MAIL_ENABLED:
        logger.info(f"Email disabled. Would send '{subject}' to {recipients}")
        return False

    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        logger.warning("Email credentials not configured, skipping send")
        return False

    try:
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=template_body,
            subtype=MessageType.html,
        )
        fm = get_fast_mail()
        await fm.send_message(message, template_name=template_name)
        logger.info(f"Email sent: '{subject}' to {recipients}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email '{subject}' to {recipients}: {e}")
        return False


async def send_welcome_email(email: str, first_name: str) -> bool:
    """Send welcome email after registration."""
    return await send_email(
        recipients=[email],
        subject="Добро пожаловать в Rouch! 🪷",
        template_name="welcome.html",
        template_body={
            "first_name": first_name,
            "app_name": settings.APP_NAME,
        },
    )


async def send_reset_password_email(email: str, first_name: str, token: str) -> bool:
    """Send password reset email."""
    reset_url = f"{settings.WEBAPP_URL}/reset-password?token={token}"
    return await send_email(
        recipients=[email],
        subject="Восстановление пароля 🔑",
        template_name="reset_password.html",
        template_body={
            "first_name": first_name,
            "reset_url": reset_url,
            "app_name": settings.APP_NAME,
        },
    )


async def send_verification_email(email: str, first_name: str, token: str) -> bool:
    """Send email verification link."""
    verify_url = f"{settings.WEBAPP_URL}/verify-email?token={token}"
    return await send_email(
        recipients=[email],
        subject="Подтверди свой email ✉️",
        template_name="verify_email.html",
        template_body={
            "first_name": first_name,
            "verify_url": verify_url,
            "app_name": settings.APP_NAME,
        },
    )
