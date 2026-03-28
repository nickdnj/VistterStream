"""
Headline Generator — AI vision API for contextual headlines + content safety.

Sends a frame snapshot + weather data to GPT-4o-mini (or Claude) and gets back:
- A contextual one-liner headline
- A safe_to_publish boolean (content safety gate)
"""

import base64
import logging
from pathlib import Path
from typing import Optional

import httpx
from openai import AsyncOpenAI

from models.shortforge import ShortForgeConfig
from utils.crypto import decrypt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a camera watching a marina/waterfront location. You generate short, informational headlines for YouTube Shorts based on what you see in the frame and the current weather conditions.

Rules:
- Keep headlines under 60 characters
- Be informational and warm, not clickbait
- Reference what's visually happening (boats, sunset, weather, activity)
- Include temperature or conditions when relevant
- Never use ALL CAPS or excessive punctuation

You must also evaluate content safety. Set safe_to_publish to false if the image contains:
- Clearly identifiable faces of people (especially children)
- License plates that are readable
- Emergency situations, accidents, or distressing scenes
- Inappropriate or offensive content

Respond with JSON only:
{
  "headline": "string",
  "safe_to_publish": true/false,
  "scene_description": "brief description of what you see"
}"""


async def generate_headline(
    frame_path: str,
    config: ShortForgeConfig,
    weather_data: Optional[dict] = None,
    location: str = "Wharfside Marina",
) -> dict:
    """
    Generate a headline from a frame snapshot using AI vision.

    Returns: {"headline": str, "safe_to_publish": bool, "scene_description": str}
    """
    # Read and encode the frame
    frame_file = Path(frame_path)
    if not frame_file.exists():
        return _fallback_headline(weather_data, location)

    with open(frame_file, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Build the user prompt with weather context
    user_prompt = f"Location: {location}\n"
    if weather_data:
        temp = weather_data.get("temperature", "")
        conditions = weather_data.get("conditions", "")
        wind = weather_data.get("wind_speed", "")
        user_prompt += f"Temperature: {temp}°F\nConditions: {conditions}\nWind: {wind} mph\n"
    user_prompt += "\nDescribe what you see and generate a headline for a YouTube Short."

    # Decrypt API key
    api_key = None
    if config.openai_api_key_enc:
        try:
            api_key = decrypt(config.openai_api_key_enc)
        except Exception:
            logger.warning("Failed to decrypt OpenAI API key")

    if not api_key:
        logger.warning("No OpenAI API key configured, using fallback headline")
        return _fallback_headline(weather_data, location)

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=config.ai_model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "low",  # minimize cost
                            },
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0.7,
        )

        import json
        result = json.loads(response.choices[0].message.content)
        return {
            "headline": result.get("headline", ""),
            "safe_to_publish": result.get("safe_to_publish", True),
            "scene_description": result.get("scene_description", ""),
        }

    except Exception:
        logger.exception("AI headline generation failed, using fallback")
        return _fallback_headline(weather_data, location)


def _fallback_headline(weather_data: Optional[dict], location: str) -> dict:
    """Generate a simple fallback headline without AI."""
    parts = [location]
    if weather_data:
        temp = weather_data.get("temperature")
        conditions = weather_data.get("conditions", "")
        if temp:
            parts.append(f"{temp}°F")
        if conditions:
            parts.append(conditions)

    headline = " — ".join(parts) if len(parts) > 1 else f"Live from {location}"
    return {
        "headline": headline,
        "safe_to_publish": True,  # fallback always safe (no AI review)
        "scene_description": "AI unavailable",
    }


async def fetch_weather_data(tempest_url: str = "http://vistter.local:8036") -> Optional[dict]:
    """Fetch current weather from TempestWeather API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{tempest_url}/api/current")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "temperature": data.get("air_temperature_f") or data.get("temperature"),
                    "conditions": data.get("conditions", ""),
                    "wind_speed": data.get("wind_avg_mph") or data.get("wind_speed"),
                    "humidity": data.get("relative_humidity"),
                }
    except Exception:
        logger.warning("Failed to fetch weather data from TempestWeather")
    return None
