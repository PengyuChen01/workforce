"""A2A Translate Agent - standalone FastAPI service for translation via DeepL.

Uses DeepL API (free tier: 500,000 chars/month).

Run: uvicorn agents.translate_agent:app --port 8003
"""

import os
import json
import logging

from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI
from agents.a2a_models import A2ARequest, A2AResponse, TaskResult, Artifact

logger = logging.getLogger("translate_agent")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="A2A Translate Agent", version="0.1.0")

DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"

# ---------- Agent Card ----------

AGENT_CARD = {
    "name": "TranslateAgent",
    "description": "Translates text between languages using DeepL API.",
    "url": "http://localhost:8003",
    "version": "0.1.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        {
            "id": "translate",
            "name": "Translate",
            "description": "Translate text. Input: JSON {text, target_lang, source_lang?}",
        }
    ],
}

# DeepL supported language codes
SUPPORTED_LANGS = {
    "EN", "DE", "FR", "ES", "PT", "IT", "NL", "PL", "RU", "JA", "ZH",
    "KO", "AR", "BG", "CS", "DA", "EL", "ET", "FI", "HU", "ID", "LT",
    "LV", "NB", "RO", "SK", "SL", "SV", "TR", "UK",
}


async def _translate(text: str, target_lang: str, source_lang: str = "") -> dict:
    """Translate text via DeepL API."""
    api_key = os.getenv("DEEPL_API_KEY", "")

    if not api_key:
        return {"success": False, "detail": "DEEPL_API_KEY not configured."}

    target_lang = target_lang.upper()
    if target_lang not in SUPPORTED_LANGS:
        return {"success": False, "detail": f"Unsupported target language: {target_lang}"}

    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "text": [text],
        "target_lang": target_lang,
    }
    if source_lang:
        body["source_lang"] = source_lang.upper()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(DEEPL_API_URL, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        translation = data["translations"][0]
        translated_text = translation["text"]
        detected_lang = translation.get("detected_source_language", "")

        logger.info(
            "Translated | %s -> %s | %d chars",
            detected_lang or source_lang, target_lang, len(text),
        )
        return {
            "success": True,
            "detail": translated_text,
            "source_lang": detected_lang,
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return {"success": False, "detail": "DeepL API key invalid or quota exceeded."}
        return {"success": False, "detail": f"DeepL API error: {e.response.status_code}"}
    except Exception as e:
        logger.error("Translate error: %s", e)
        return {"success": False, "detail": str(e)}


@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD


@app.post("/a2a")
async def handle_a2a(request: A2ARequest) -> A2AResponse:
    """Handle A2A request - parse translation JSON and translate."""
    task_id = request.params.id

    text_parts = [p.text for p in request.params.message.parts if p.type == "text"]
    full_text = " ".join(text_parts)

    try:
        params = json.loads(full_text)
    except json.JSONDecodeError:
        return A2AResponse(
            result=TaskResult(
                id=task_id,
                status="failed",
                artifacts=[Artifact(text=f"Invalid input. Expected JSON with text/target_lang. Got: {full_text}")],
            )
        )

    text = params.get("text", "")
    target_lang = params.get("target_lang", "EN")
    source_lang = params.get("source_lang", "")

    if not text:
        return A2AResponse(
            result=TaskResult(
                id=task_id,
                status="failed",
                artifacts=[Artifact(text="No text provided to translate.")],
            )
        )

    result = await _translate(text=text, target_lang=target_lang, source_lang=source_lang)

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
    return {"status": "ok", "agent": "translate", "version": "0.1.0"}
