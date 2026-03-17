"""Speech-to-Text service using OpenAI Whisper API."""

import io
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe audio bytes to text using Whisper.

    Args:
        audio_bytes: Raw audio file bytes.
        filename: Original filename (used to infer format).

    Returns:
        Transcribed text string.
    """
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )
    return response.text
