"""A2A Weather Agent - standalone FastAPI service for real-time weather.

Uses OpenWeatherMap API (free tier, 1000 calls/day).

Run: uvicorn agents.weather_agent:app --port 8002
"""

import os
import json
import logging

from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI
from agents.a2a_models import A2ARequest, A2AResponse, TaskResult, Artifact

logger = logging.getLogger("weather_agent")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="A2A Weather Agent", version="0.1.0")

OWM_BASE = "https://api.openweathermap.org/data/2.5/weather"

# ---------- Agent Card ----------

AGENT_CARD = {
    "name": "WeatherAgent",
    "description": "Provides real-time weather information for any city worldwide.",
    "url": "http://localhost:8002",
    "version": "0.1.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        {
            "id": "weather",
            "name": "Get Weather",
            "description": "Get current weather for a city. Input: JSON {city, units}",
        }
    ],
}


async def _get_weather(city: str, units: str = "imperial") -> dict:
    """Fetch weather from OpenWeatherMap."""
    api_key = os.getenv("OPENWEATHER_API_KEY", "")

    if not api_key:
        return {"success": False, "detail": "OPENWEATHER_API_KEY not configured."}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                OWM_BASE,
                params={"q": city, "appid": api_key, "units": units, "lang": "en"},
            )
            resp.raise_for_status()
            data = resp.json()

        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc = data["weather"][0]["description"]
        wind = data["wind"]["speed"]
        name = data["name"]
        country = data["sys"]["country"]

        u = "F" if units == "imperial" else "C"
        su = "mph" if units == "imperial" else "m/s"

        summary = (
            f"Weather in {name}, {country}: {desc}. "
            f"Temperature: {temp:.0f}{u} (feels like {feels_like:.0f}{u}). "
            f"Humidity: {humidity}%. Wind: {wind} {su}."
        )

        logger.info("Weather fetched | city=%s | temp=%s%s", name, temp, u)
        return {"success": True, "detail": summary}

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"success": False, "detail": f"City '{city}' not found."}
        return {"success": False, "detail": f"API error: {e.response.status_code}"}
    except Exception as e:
        logger.error("Weather error: %s", e)
        return {"success": False, "detail": str(e)}


@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD


@app.post("/a2a")
async def handle_a2a(request: A2ARequest) -> A2AResponse:
    """Handle A2A request - parse city JSON and fetch weather."""
    task_id = request.params.id

    text_parts = [p.text for p in request.params.message.parts if p.type == "text"]
    full_text = " ".join(text_parts)

    try:
        params = json.loads(full_text)
    except json.JSONDecodeError:
        # Treat raw text as city name
        params = {"city": full_text.strip(), "units": "imperial"}

    city = params.get("city", "")
    units = params.get("units", "imperial")

    result = await _get_weather(city=city, units=units)

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
    return {"status": "ok", "agent": "weather", "version": "0.1.0"}
