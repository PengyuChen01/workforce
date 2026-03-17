"""Weather service using OpenWeatherMap API (free tier)."""

import os
import logging
import httpx

logger = logging.getLogger("weather-service")

API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def is_configured() -> bool:
    return bool(os.getenv("OPENWEATHER_API_KEY"))


async def get_weather(city: str, units: str = "metric") -> dict:
    """Fetch current weather for a city.

    Args:
        city: City name (e.g. "Columbus", "Columbus, OH")
        units: "metric" (Celsius) or "imperial" (Fahrenheit)

    Returns:
        dict with success, and weather details or error.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY", "")

    if not api_key:
        return {"success": False, "detail": "OPENWEATHER_API_KEY not configured."}

    if not city:
        return {"success": False, "detail": "No city provided."}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                BASE_URL,
                params={
                    "q": city,
                    "appid": api_key,
                    "units": units,
                    "lang": "en",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        description = data["weather"][0]["description"]
        wind_speed = data["wind"]["speed"]
        city_name = data["name"]
        country = data["sys"]["country"]

        unit_label = "C" if units == "metric" else "F"
        speed_label = "m/s" if units == "metric" else "mph"

        return {
            "success": True,
            "city": f"{city_name}, {country}",
            "temp": f"{temp:.0f} degrees {unit_label}",
            "feels_like": f"{feels_like:.0f} degrees {unit_label}",
            "description": description,
            "humidity": f"{humidity}%",
            "wind": f"{wind_speed} {speed_label}",
            "summary": (
                f"Weather in {city_name}, {country}: {description}. "
                f"Temperature: {temp:.0f} degrees {unit_label} (feels like {feels_like:.0f}). "
                f"Humidity: {humidity}%. Wind: {wind_speed} {speed_label}."
            ),
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"success": False, "detail": f"City '{city}' not found."}
        return {"success": False, "detail": f"Weather API error: {e.response.status_code}"}
    except Exception as e:
        logger.error("Weather fetch error: %s", e)
        return {"success": False, "detail": f"Weather error: {e}"}
