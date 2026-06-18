"""Outgoing email via the SMTP settings stored in the Settings table.

The appliance has no built-in mail service, so the admin configures SMTP
(host/port/username/password/from) in Settings. The password is stored
encrypted at rest (Fernet, see utils/crypto.py) and decrypted only when a
message is actually sent.
"""

import smtplib
import ssl
import logging
from email.message import EmailMessage
from typing import Optional

from models.database import Settings
from utils.crypto import decrypt

logger = logging.getLogger(__name__)


class EmailNotConfigured(Exception):
    """Raised when SMTP settings are incomplete."""


class EmailSendError(Exception):
    """Raised when the SMTP server rejects or fails to deliver a message."""


def is_configured(settings: Optional[Settings]) -> bool:
    """True when the minimum SMTP fields are present to send mail."""
    return bool(
        settings
        and settings.smtp_host
        and settings.smtp_port
        and settings.smtp_from_address
    )


def send_email(settings: Optional[Settings], to_address: str, subject: str, body: str) -> None:
    """Send a plaintext email using the configured SMTP settings.

    Raises EmailNotConfigured if settings are incomplete, EmailSendError on
    any SMTP/connection failure.
    """
    if not is_configured(settings):
        raise EmailNotConfigured(
            "SMTP is not configured. Set the mail server fields under Settings > Account."
        )
    assert settings is not None  # narrowed by is_configured()

    msg = EmailMessage()
    msg["From"] = settings.smtp_from_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    password = ""
    if settings.smtp_password_encrypted:
        try:
            password = decrypt(settings.smtp_password_encrypted)
        except Exception as exc:  # noqa: BLE001
            raise EmailSendError(f"Could not decrypt SMTP password: {exc}") from exc

    host = settings.smtp_host
    port = int(settings.smtp_port)
    use_tls = settings.smtp_use_tls if settings.smtp_use_tls is not None else True

    try:
        if port == 465:
            # Implicit TLS
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as server:
                if settings.smtp_username:
                    server.login(settings.smtp_username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                if settings.smtp_username:
                    server.login(settings.smtp_username, password)
                server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Failed to send email to %s: %s", to_address, exc)
        raise EmailSendError(str(exc)) from exc

    logger.info("Sent email to %s (subject: %s)", to_address, subject)
