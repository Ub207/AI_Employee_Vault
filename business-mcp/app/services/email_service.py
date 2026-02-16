"""
Email service — sends mail via SMTP (TLS).
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.services.log_service import log_activity


def send_email(to: str, subject: str, body: str) -> dict:
    """
    Send a plain-text email via the configured SMTP server.
    Returns a result dict with status and detail.
    """
    if not settings.smtp_user or not settings.smtp_password:
        detail = "SMTP credentials not configured in .env"
        log_activity("send_email", detail, status="ERROR")
        return {"status": "error", "detail": detail}

    msg = MIMEMultipart()
    msg["From"] = settings.email_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(msg["From"], [to], msg.as_string())

        detail = f"Email sent to {to} — subject: {subject}"
        log_activity("send_email", detail)
        return {"status": "ok", "detail": detail}

    except smtplib.SMTPAuthenticationError as exc:
        detail = f"SMTP auth failed: {exc.smtp_error}"
        log_activity("send_email", detail, status="ERROR")
        return {"status": "error", "detail": detail}

    except smtplib.SMTPException as exc:
        detail = f"SMTP error: {exc}"
        log_activity("send_email", detail, status="ERROR")
        return {"status": "error", "detail": detail}

    except OSError as exc:
        detail = f"Network error: {exc}"
        log_activity("send_email", detail, status="ERROR")
        return {"status": "error", "detail": detail}
