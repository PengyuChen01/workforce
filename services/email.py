"""Email sending service via Resend API."""

import os
import logging
import resend

logger = logging.getLogger("email-service")


def is_configured() -> bool:
    """Check if Resend API key is set."""
    return bool(os.getenv("RESEND_API_KEY"))


async def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email via Resend API.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text.

    Returns:
        dict with "success" and "detail" keys.
    """
    api_key = os.getenv("RESEND_API_KEY", "")

    if not api_key:
        return {
            "success": False,
            "detail": "RESEND_API_KEY not configured in .env",
        }

    if not to:
        return {"success": False, "detail": "No recipient email address provided."}

    resend.api_key = api_key
    from_email = os.getenv("RESEND_FROM", "onboarding@resend.dev")

    try:
        result = resend.Emails.send({
            "from": from_email,
            "to": [to],
            "subject": subject or "(No subject)",
            "text": body or "",
        })
        logger.info("Email sent via Resend | to=%s | subject=%s | id=%s", to, subject, result.get("id"))
        return {
            "success": True,
            "detail": f"Email sent to {to} with subject \"{subject}\".",
        }
    except Exception as e:
        logger.error("Resend error: %s", e)
        return {"success": False, "detail": f"Resend error: {e}"}
