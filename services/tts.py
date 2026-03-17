"""Text-to-Speech service using ElevenLabs streaming API (optional)."""

import os
import logging
from typing import AsyncIterator

logger = logging.getLogger("tts")

# Check if ElevenLabs is available
_tts_available = False
_client = None

try:
    from elevenlabs.client import AsyncElevenLabs
    if os.getenv("ELEVENLABS_API_KEY"):
        _tts_available = True
except ImportError:
    logger.warning("elevenlabs package not installed, TTS disabled.")


def is_available() -> bool:
    """Check if TTS service is configured and available."""
    return _tts_available and bool(os.getenv("ELEVENLABS_API_KEY"))


def _get_client() -> "AsyncElevenLabs":
    global _client
    if _client is None:
        from elevenlabs.client import AsyncElevenLabs
        _client = AsyncElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    return _client


async def synthesise(text: str) -> AsyncIterator[bytes]:
    """Stream TTS audio chunks for the given text.

    Args:
        text: The text to convert to speech.

    Yields:
        Audio bytes chunks (mp3 format).

    Raises:
        RuntimeError: If TTS is not configured.
    """
    if not is_available():
        raise RuntimeError(
            "TTS not configured. Set ELEVENLABS_API_KEY in .env to enable."
        )

    client = _get_client()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel

    audio_stream = await client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    for chunk in audio_stream:
        if chunk:
            yield chunk
