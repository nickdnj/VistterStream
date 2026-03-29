"""
Narration Engine — AI script + TTS + word timing for TikTok-style shorts.

Generates a punchy 10-15 second narration script from weather/scene data,
converts to speech via OpenAI TTS, and computes per-word timing for
synchronized text overlay.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

from models.shortforge import ShortForgeConfig
from utils.crypto import decrypt

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")
AUDIO_DIR = DATA_DIR / "audio"

NARRATION_PROMPT = """You write short, punchy voiceover scripts for 15-second YouTube Shorts filmed at a waterfront marina.

Your style is:
- Fun, warm, slightly irreverent — like a friend sharing their favorite view
- Short punchy sentences, 3-4 sentences max
- Reference specific details: weather, temperature, time of day, what's happening
- Make it feel alive — paint a picture with words
- End with something memorable or witty

You get weather data and a scene description. Write a narration script that someone would actually want to listen to.

Important:
- Total length: 20-40 words (fits in ~12 seconds of speech)
- No hashtags, no emojis, no "subscribe" calls to action
- Write conversationally — this will be spoken aloud

Respond with JSON only:
{
  "narration": "The full voiceover script",
  "title": "Short catchy title for YouTube (under 60 chars)"
}"""


async def generate_narration(
    scene_description: str,
    config: ShortForgeConfig,
    weather_data: Optional[dict] = None,
    location: str = "Wharfside Marina",
) -> dict:
    """
    Generate a narration script using AI.

    Returns: {"narration": str, "title": str}
    """
    api_key = None
    if config.openai_api_key_enc:
        try:
            api_key = decrypt(config.openai_api_key_enc)
        except Exception:
            pass

    if not api_key:
        return _fallback_narration(weather_data, location)

    # Build context
    now = datetime.now(timezone.utc)
    hour = (now.hour - 4) % 24  # rough EDT conversion
    time_of_day = "morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 17 else "evening" if 17 <= hour < 21 else "night"

    context = f"Location: {location}\nTime: {time_of_day}\n"
    if weather_data:
        temp = weather_data.get("temperature", "")
        conditions = weather_data.get("conditions", "")
        wind = weather_data.get("wind_speed", "")
        humidity = weather_data.get("humidity", "")
        if temp:
            context += f"Temperature: {temp}°F\n"
        if conditions:
            context += f"Conditions: {conditions}\n"
        if wind:
            context += f"Wind: {wind} mph\n"
        if humidity:
            context += f"Humidity: {humidity}%\n"
    if scene_description:
        context += f"\nScene: {scene_description}\n"

    context += "\nWrite a fun voiceover script for this moment."

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=config.ai_model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": NARRATION_PROMPT},
                {"role": "user", "content": context},
            ],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0.9,
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "narration": result.get("narration", ""),
            "title": result.get("title", ""),
        }
    except Exception:
        logger.exception("Narration generation failed")
        return _fallback_narration(weather_data, location)


async def generate_tts(
    text: str,
    clip_id: int,
    config: ShortForgeConfig,
    voice: str = "shimmer",
) -> Optional[str]:
    """
    Generate TTS audio from narration text using OpenAI.

    Returns path to the audio file, or None on failure.
    """
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    api_key = None
    if config.openai_api_key_enc:
        try:
            api_key = decrypt(config.openai_api_key_enc)
        except Exception:
            pass

    if not api_key:
        logger.warning("No OpenAI API key for TTS")
        return None

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input=text,
            speed=0.95,  # natural, unhurried delivery
        )

        audio_path = AUDIO_DIR / f"narration_{clip_id}.mp3"
        response.stream_to_file(str(audio_path))
        logger.info("TTS generated: %s (voice=%s)", audio_path, voice)
        return str(audio_path)

    except Exception:
        logger.exception("TTS generation failed for clip %d", clip_id)
        return None


def compute_word_timings(text: str, audio_duration: float) -> list[dict]:
    """
    Compute approximate per-word timing for text overlay.

    Returns list of {"word": str, "start": float, "end": float}
    """
    words = text.split()
    if not words:
        return []

    # Simple proportional timing based on word length
    # (longer words take proportionally more time to speak)
    total_chars = sum(len(w) for w in words)
    if total_chars == 0:
        return []

    # Leave a small gap at start and end
    margin = 0.3
    available = audio_duration - (2 * margin)
    if available <= 0:
        available = audio_duration

    current_time = margin
    timings = []
    for word in words:
        word_duration = (len(word) / total_chars) * available
        # Minimum word duration
        word_duration = max(word_duration, 0.15)
        timings.append({
            "word": word,
            "start": round(current_time, 3),
            "end": round(current_time + word_duration, 3),
        })
        current_time += word_duration

    return timings


def build_word_overlay_filter(timings: list[dict], font: str = "DejaVu Sans") -> str:
    """
    Build FFmpeg drawtext filter chain for word-by-word TikTok-style overlay.

    Each word pops on screen at its start time and stays until the next word appears.
    Words are displayed one at a time, centered near the top of the frame.
    """
    if not timings:
        return ""

    parts = []
    for i, t in enumerate(timings):
        word = t["word"].replace("'", "'\\\\\\''").replace(":", "\\:").replace("%", "%%")
        start = t["start"]
        # Word stays visible until next word starts (or end of its own duration + 0.1)
        end = timings[i + 1]["start"] if i + 1 < len(timings) else t["end"] + 0.5

        parts.append(
            f"drawtext=text='{word}'"
            f":fontsize=84:fontcolor=white:borderw=5:bordercolor=black"
            f":x=(w-text_w)/2:y=160"
            f":font={font}"
            f":enable='between(t,{start:.3f},{end:.3f})'"
        )

    return ",".join(parts)


MUSIC_DIR = DATA_DIR / "music"


async def get_music_bed(duration: float = 30.0) -> Optional[str]:
    """
    Get or generate an ambient music bed for shorts.
    Creates a warm ambient pad using FFmpeg synthesis (no external files needed).
    Returns path to the music file.
    """
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    music_path = MUSIC_DIR / "ambient_pad.mp3"

    # Reuse existing music bed if it exists
    if music_path.exists():
        return str(music_path)

    # Generate a warm ambient pad: A minor chord (A2 + C3 + E3) with reverb
    import asyncio
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=110:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=131:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=165:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration}",
        "-filter_complex",
        "[0]volume=0.3[a];[1]volume=0.25[b];[2]volume=0.2[c];[3]volume=0.15[d];"
        "[a][b][c][d]amix=inputs=4:duration=longest,"
        "lowpass=f=600,highpass=f=80,"
        "afade=t=in:d=2,afade=t=out:st=" + f"{duration - 3}" + ":d=3",
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(music_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        if music_path.exists():
            logger.info("Generated ambient music bed: %s", music_path)
            return str(music_path)
    except Exception:
        logger.exception("Failed to generate music bed")
    return None


async def mix_narration_with_music(
    narration_path: str,
    clip_id: int,
    music_volume: float = 0.12,
) -> Optional[str]:
    """
    Mix narration audio with background music bed.
    Returns path to the mixed audio file.
    """
    import asyncio

    music_path = await get_music_bed()
    if not music_path:
        return narration_path  # fallback: just the narration

    mixed_path = AUDIO_DIR / f"mixed_{clip_id}.mp3"

    cmd = [
        "ffmpeg", "-y",
        "-i", narration_path,
        "-i", music_path,
        "-filter_complex",
        f"[0:a]volume=1.0[narr];"
        f"[1:a]volume={music_volume}[music];"
        f"[narr][music]amix=inputs=2:duration=first:dropout_transition=2[out]",
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(mixed_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0 and mixed_path.exists():
            logger.info("Mixed narration + music: %s", mixed_path)
            return str(mixed_path)
        else:
            error = stderr[-200:].decode(errors="replace") if stderr else ""
            logger.warning("Audio mix failed: %s", error)
    except Exception:
        logger.exception("Failed to mix narration with music")

    return narration_path  # fallback: just the narration


def _fallback_narration(weather_data: Optional[dict], location: str) -> dict:
    """Simple fallback narration without AI."""
    parts = [f"Live from {location}."]
    if weather_data:
        temp = weather_data.get("temperature")
        conditions = weather_data.get("conditions", "")
        if temp:
            parts.append(f"Currently {temp} degrees.")
        if conditions:
            parts.append(conditions + ".")
    parts.append("Another beautiful day on the water.")

    return {
        "narration": " ".join(parts),
        "title": f"Live from {location}",
    }
