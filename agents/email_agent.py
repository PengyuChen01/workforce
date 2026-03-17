"""A2A Email Agent - standalone FastAPI service that sends real emails via Resend.

Run: uvicorn agents.email_agent:app --port 8001
"""

import os
import json
import logging

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from agents.a2a_models import A2ARequest, A2AResponse, TaskResult, Artifact

logger = logging.getLogger("email_agent")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="A2A Email Agent", version="0.2.0")

# ---------- Agent Card ----------

AGENT_CARD = {
    "name": "EmailAgent",
    "description": "Sends real emails via Resend API. Accepts JSON with to, subject, body.",
    "url": "http://localhost:8001",
    "version": "0.2.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        {
            "id": "send_email",
            "name": "Send Email",
            "description": "Send an email. Input: JSON {to, subject, body}",
        }
    ],
}


async def _send_email(to: str, subject: str, body: str) -> dict:
    """Send email via Resend API."""
    import resend

    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        return {"success": False, "detail": "RESEND_API_KEY not configured."}

    resend.api_key = api_key
    from_email = os.getenv("RESEND_FROM", "onboarding@resend.dev")

    try:
        result = resend.Emails.send({
            "from": from_email,
            "to": [to],
            "subject": subject or "(No subject)",
            "text": body or "",
        })
        logger.info("Email sent | to=%s | subject=%s | id=%s", to, subject, result.get("id"))
        return {"success": True, "detail": f"Email sent to {to} with subject \"{subject}\"."}
    except Exception as e:
        logger.error("Resend error: %s", e)
        return {"success": False, "detail": str(e)}


@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD


@app.post("/a2a")
async def handle_a2a(request: A2ARequest) -> A2AResponse:
    """Handle A2A request - parse email JSON from message and send."""
    task_id = request.params.id

    # The orchestrator sends structured JSON in the message text
    text_parts = [p.text for p in request.params.message.parts if p.type == "text"]
    full_text = " ".join(text_parts)

    # Try to parse as JSON first (structured input from orchestrator)
    try:
        email_data = json.loads(full_text)
    except json.JSONDecodeError:
        return A2AResponse(
            result=TaskResult(
                id=task_id,
                status="failed",
                artifacts=[Artifact(text=f"Invalid input. Expected JSON with to/subject/body. Got: {full_text}")],
            )
        )

    to = email_data.get("to", "")
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")

    result = await _send_email(to=to, subject=subject, body=body)

    status = "completed" if result["success"] else "failed"
    return A2AResponse(
        result=TaskResult(
            id=task_id,
            status=status,
            artifacts=[Artifact(text=result["detail"])],
        )
    )


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "email", "version": "0.2.0"}
