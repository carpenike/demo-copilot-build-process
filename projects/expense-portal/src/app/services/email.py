"""Email sending service (FR-022)."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def send_email(to_address: str, subject: str, body_html: str) -> None:
    """Send a transactional email via the corporate SMTP relay."""
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        logger.info("email_sent", to=to_address, subject=subject)
    except Exception:
        logger.exception("email_send_failed", to=to_address, subject=subject)
        raise
