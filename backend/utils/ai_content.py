"""
AI Content Generation for ReelForge
Ported from d3marco's seaer_ai/seaer_app.py with modifications for VistterStream.

Generates headlines and content for social media posts using AI.
Settings (API key, model, system prompt) are loaded from the database.
"""

import json
import logging
import base64
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. AI content generation will use placeholders.")


def get_reelforge_settings() -> Tuple[Optional[str], str, str, float, int]:
    """
    Get ReelForge settings from the database.
    
    Returns:
        Tuple of (api_key, model, system_prompt, temperature, max_tokens)
    """
    from models.database import SessionLocal, ReelForgeSettings
    
    db = SessionLocal()
    try:
        settings = db.query(ReelForgeSettings).first()
        
        if not settings:
            return (None, "gpt-4o-mini", get_default_system_prompt(), 0.8, 500)
        
        api_key = None
        if settings.openai_api_key_enc:
            try:
                api_key = base64.b64decode(settings.openai_api_key_enc.encode()).decode()
            except:
                pass
        
        return (
            api_key,
            settings.openai_model or "gpt-4o-mini",
            settings.system_prompt or get_default_system_prompt(),
            settings.temperature or 0.8,
            settings.max_tokens or 500
        )
    finally:
        db.close()


def get_default_system_prompt() -> str:
    """Get the default system prompt"""
    return """You are a social media content creator specializing in short-form video content like TikTok, Instagram Reels, and YouTube Shorts. You create short, punchy headlines that grab attention.

Guidelines:
- Keep headlines SHORT (under 10 words)
- Make them engaging and scroll-stopping
- Match the tone and voice specified
- Use current date/time context when relevant
- Always respond with valid JSON only"""


def format_prompt(ai_config: Dict) -> str:
    """
    Format the AI prompt from configuration.
    
    ai_config structure:
    {
        "tone": "casual",
        "voice": "friendly surf instructor",
        "instructions": "Create engaging content...",
        "prompt_1": "Morning greeting",
        "prompt_2": "Weather update",
        "prompt_3": "Highlight",
        "prompt_4": "Call to action",
        "prompt_5": "Sign off"
    }
    """
    instructions = ai_config.get('instructions', 'Create engaging short-form video content.')
    voice = ai_config.get('voice', 'friendly guide')
    tone = ai_config.get('tone', 'casual')
    
    prompts = [
        ai_config.get(f'prompt_{i}', f'Content point {i}')
        for i in range(1, 6)
    ]
    
    # Get current date/time for dynamic content
    now = datetime.now()
    time_of_day = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
    date_str = now.strftime("%B %d, %Y")
    
    # Build the prompt
    prompt = f"""You are creating headlines for short-form video content (like TikTok, Instagram Reels, YouTube Shorts).

STYLE REQUIREMENTS:
- Tone: {tone}
- Voice: {voice}
- Keep each headline SHORT (under 10 words ideally)
- Make them punchy and engaging for social media
- Current date: {date_str}
- Time of day: {time_of_day}

CONTENT INSTRUCTIONS:
{instructions}

Generate exactly 5 headlines based on these prompts:
1. {prompts[0]}
2. {prompts[1]}
3. {prompts[2]}
4. {prompts[3]}
5. {prompts[4]}

Return ONLY a JSON object with this exact structure:
{{
    "headline_1": "Your first headline here",
    "headline_2": "Your second headline here",
    "headline_3": "Your third headline here",
    "headline_4": "Your fourth headline here",
    "headline_5": "Your fifth headline here"
}}

Return ONLY the JSON, no other text."""

    return prompt


def extract_headlines_from_response(response_text: str) -> List[str]:
    """Extract headlines from AI response"""
    try:
        # Try to parse as JSON
        data = json.loads(response_text)
        
        headlines = []
        for i in range(1, 6):
            key = f"headline_{i}"
            if key in data:
                headlines.append(data[key])
        
        if headlines:
            return headlines
            
    except json.JSONDecodeError:
        logger.warning("Failed to parse AI response as JSON, trying text extraction")
    
    # Fallback: try to extract lines that look like headlines
    lines = response_text.strip().split('\n')
    headlines = []
    for line in lines:
        line = line.strip()
        # Skip empty lines and JSON artifacts
        if line and not line.startswith('{') and not line.startswith('}'):
            # Remove numbering if present
            if line[0].isdigit() and '.' in line[:3]:
                line = line.split('.', 1)[1].strip()
            # Remove quotes
            line = line.strip('"\'')
            if line:
                headlines.append(line)
    
    return headlines[:5]


async def generate_headlines(ai_config: Dict) -> List[str]:
    """
    Generate 5 headlines using AI based on the configuration.
    
    Settings (API key, model, system prompt) are loaded from the database.
    
    Returns list of 5 headline strings.
    """
    
    # Get settings from database
    api_key, model, system_prompt, temperature, max_tokens = get_reelforge_settings()
    
    if not OPENAI_AVAILABLE or not api_key:
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI package not available, generating placeholder headlines")
        else:
            logger.warning("No API key configured, generating placeholder headlines")
        return generate_placeholder_headlines(ai_config)
    
    try:
        # Set API key
        openai.api_key = api_key
        
        # Format the prompt
        prompt = format_prompt(ai_config)
        
        logger.info(f"Generating headlines with model={model}, temp={temperature}")
        
        # Make API call
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        
        # Extract response
        response_text = response['choices'][0]['message']['content'].strip()
        
        # Parse headlines
        headlines = extract_headlines_from_response(response_text)
        
        if len(headlines) >= 5:
            logger.info(f"Generated {len(headlines)} AI headlines")
            return headlines[:5]
        else:
            logger.warning(f"Only got {len(headlines)} headlines, padding with placeholders")
            while len(headlines) < 5:
                headlines.append(f"Check out more! #{len(headlines) + 1}")
            return headlines
            
    except Exception as e:
        logger.error(f"AI headline generation failed: {e}")
        return generate_placeholder_headlines(ai_config)


def generate_placeholder_headlines(ai_config: Dict) -> List[str]:
    """Generate placeholder headlines when AI is not available"""
    
    now = datetime.now()
    time_of_day = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
    
    tone = ai_config.get('tone', 'casual')
    
    if tone == 'professional':
        return [
            f"Good {time_of_day}!",
            "Here's your update",
            "What you need to know",
            "Visit us today",
            "Thanks for watching!"
        ]
    else:
        return [
            f"Hey! Happy {time_of_day}!",
            "Check this out!",
            "You won't believe this!",
            "Come hang with us!",
            "See you next time!"
        ]


async def generate_headlines_with_data(
    ai_config: Dict,
    weather_data: Optional[Dict] = None,
    custom_data: Optional[Dict] = None
) -> List[str]:
    """
    Generate headlines with additional contextual data.
    
    This extended version allows passing weather data, custom variables, etc.
    to make the content more dynamic and relevant.
    """
    
    # Build extended instructions with data
    extended_config = ai_config.copy()
    
    instructions = extended_config.get('instructions', '')
    
    # Add weather data if provided
    if weather_data:
        weather_context = f"""
Current conditions:
- Temperature: {weather_data.get('temperature', 'N/A')}
- Conditions: {weather_data.get('conditions', 'N/A')}
- Wind: {weather_data.get('wind_speed', 'N/A')} {weather_data.get('wind_direction', '')}
"""
        instructions = instructions + "\n\n" + weather_context
    
    # Add custom data if provided
    if custom_data:
        custom_context = "\nAdditional context:\n"
        for key, value in custom_data.items():
            custom_context += f"- {key}: {value}\n"
        instructions = instructions + custom_context
    
    extended_config['instructions'] = instructions
    
    return await generate_headlines(extended_config)


# Sync wrapper for non-async contexts
def generate_headlines_sync(ai_config: Dict) -> List[str]:
    """Synchronous wrapper for generate_headlines"""
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(generate_headlines(ai_config))
