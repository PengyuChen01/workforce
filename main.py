"""Voice Agent MVP - FastAPI entrypoint.

Endpoints:
    POST /voice       - Upload audio, get text response
    POST /text        - Text input, get text response
    POST /webhook     - Generic webhook for external channels (WeChat, etc.)
    GET  /skills      - List available skills
    GET  /health      - Health check
"""

import os
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from services.channel import process_message
from services.stt import transcribe
from skills.registry import list_skills

logger = logging.getLogger("voice-agent")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Voice Agent MVP", version="0.2.0")


# ---------- Request / Response models ----------

class TextRequest(BaseModel):
    text: str
    user_id: str = ""


class AgentResponse(BaseModel):
    transcript: str
    selected_skill: str
    response_text: str
    error: str | None = None
    channel: str = "api"


class WebhookRequest(BaseModel):
    """Generic webhook payload. Adapt for WeChat / Telegram / Slack etc."""
    text: str
    channel: str = "webhook"
    user_id: str = ""
    metadata: dict | None = None


# ---------- Endpoints ----------

@app.post("/voice", response_model=AgentResponse)
async def voice_endpoint(audio: UploadFile = File(...)):
    """Upload audio -> STT -> skill router -> skill executor -> text response."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    logger.info("Transcribing audio (%d bytes)...", len(audio_bytes))
    transcript = await transcribe(audio_bytes, filename=audio.filename or "audio.webm")
    logger.info("Transcript: %s", transcript)

    result = await process_message(transcript, channel="voice")
    return AgentResponse(**result)


@app.post("/text", response_model=AgentResponse)
async def text_endpoint(req: TextRequest):
    """Text input -> skill router -> skill executor -> text response."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text.")

    logger.info("Text input: %s", req.text)
    result = await process_message(req.text, channel="api", user_id=req.user_id)
    return AgentResponse(**result)


@app.post("/webhook", response_model=AgentResponse)
async def webhook_endpoint(req: WebhookRequest):
    """Generic webhook endpoint for external messaging channels.

    Use this to connect WeChat, Telegram, Slack, etc.
    Each channel adapter parses its native format into this payload.

    Example WeChat integration:
        1. WeChat sends message to your server
        2. Your adapter extracts text and calls POST /webhook
        3. Response text gets sent back to WeChat user
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text.")

    logger.info("[%s] user=%s: %s", req.channel, req.user_id, req.text)
    result = await process_message(req.text, channel=req.channel, user_id=req.user_id)
    return AgentResponse(**result)


@app.get("/skills")
async def skills_endpoint():
    """List all available skills."""
    return {"skills": list_skills()}


@app.get("/agents")
async def agents_endpoint():
    """Discover all A2A agents by fetching their agent cards."""
    import httpx

    agent_urls = [s["agent_url"] for s in list_skills() if s.get("agent_url")]
    agents = []

    async with httpx.AsyncClient(timeout=5.0) as client:
        for url in agent_urls:
            try:
                resp = await client.get(f"{url}/.well-known/agent.json")
                resp.raise_for_status()
                card = resp.json()
                card["status"] = "online"
                agents.append(card)
            except Exception:
                agents.append({"url": url, "status": "offline"})

    return {"agents": agents}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "voice-agent", "version": "0.3.0"}
