"""
Weather Data Service for ReelForge
Fetches environmental data from TempestWeather API for use in AI headline generation.

Data sources via TempestWeather:
- Tempest Weather Network (temperature, wind, humidity, pressure, etc.)
- NOAA Tides & Currents (tide stage, next tide)
- NOAA Water Temperature
- Astronomy calculations (moon phase, solunar periods)
"""

import logging
import httpx
from datetime import datetime
from typing import Dict, Optional
import base64

logger = logging.getLogger(__name__)

# Default TempestWeather URL (can be overridden in settings)
DEFAULT_TEMPEST_URL = "http://tempest-weather:8085"


def get_tempest_api_url() -> str:
    """Get the TempestWeather API URL from settings"""
    try:
        from models.database import SessionLocal, ReelForgeSettings
        
        db = SessionLocal()
        try:
            settings = db.query(ReelForgeSettings).first()
            if settings and settings.tempest_api_url:
                return settings.tempest_api_url
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not get TempestWeather URL from settings: {e}")
    
    return DEFAULT_TEMPEST_URL


def is_weather_enabled() -> bool:
    """Check if weather integration is enabled in settings"""
    try:
        from models.database import SessionLocal, ReelForgeSettings
        
        db = SessionLocal()
        try:
            settings = db.query(ReelForgeSettings).first()
            if settings:
                return settings.weather_enabled if settings.weather_enabled is not None else True
        finally:
            db.close()
    except Exception:
        pass
    
    return True


async def fetch_weather_data(units: str = "imperial") -> Optional[Dict]:
    """
    Fetch all weather data from TempestWeather API.
    
    Args:
        units: 'imperial' or 'metric'
    
    Returns:
        Dictionary with all weather variables, or None if fetch fails
    """
    if not is_weather_enabled():
        logger.debug("Weather integration is disabled")
        return None
    
    api_url = get_tempest_api_url()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{api_url}/api/data",
                params={"units": units}
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse and flatten the data into template variables
            return parse_weather_data(data, units)
            
    except httpx.ConnectError:
        logger.warning(f"Could not connect to TempestWeather at {api_url}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"TempestWeather API error: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None


def fetch_weather_data_sync(units: str = "imperial") -> Optional[Dict]:
    """Synchronous version of fetch_weather_data"""
    if not is_weather_enabled():
        return None
    
    api_url = get_tempest_api_url()
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{api_url}/api/data",
                params={"units": units}
            )
            response.raise_for_status()
            data = response.json()
            
            return parse_weather_data(data, units)
            
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None


def parse_weather_data(raw_data: Dict, units: str = "imperial") -> Dict:
    """
    Parse raw TempestWeather API response into flat template variables.
    
    Args:
        raw_data: Raw JSON from TempestWeather /api/data endpoint
        units: 'imperial' or 'metric'
    
    Returns:
        Dictionary of template variables
    """
    variables = {}
    
    # System variables (always available)
    now = datetime.now()
    variables["today_date"] = now.strftime("%B %d, %Y")
    variables["day_of_week"] = now.strftime("%A")
    hour = now.hour
    if hour < 12:
        variables["time_of_day"] = "morning"
    elif hour < 17:
        variables["time_of_day"] = "afternoon"
    else:
        variables["time_of_day"] = "evening"
    variables["current_time"] = now.strftime("%I:%M %p").lstrip("0")
    
    # Parse current conditions
    current = raw_data.get("current", {})
    if current:
        variables["temperature"] = current.get("temperature", "--")
        variables["feels_like"] = current.get("feels_like", "--")
        variables["humidity"] = current.get("humidity", "--")
        variables["wind"] = current.get("wind", "--")
        variables["wind_gust"] = current.get("wind_gust", "--")
        variables["conditions"] = current.get("conditions", "")
        variables["pressure"] = current.get("pressure", "--")
        variables["uv_index"] = current.get("uv_index", "--")
        variables["rain_today"] = current.get("rain_today", "--")
        variables["location"] = current.get("location_name", "")
    
    # Parse fishing/tide data
    fishing = raw_data.get("fishing", {})
    if fishing:
        variables["tide_stage"] = fishing.get("tide_stage", "--")
        variables["next_tide"] = fishing.get("next_tide_event", "--")
        variables["next_tide_time"] = fishing.get("next_tide_time", "--")
        variables["tide_height"] = fishing.get("tide_height", "--")
        variables["moon_phase"] = fishing.get("moon_phase", "--")
        variables["moon_illumination"] = fishing.get("moon_illumination", "--")
        variables["water_temp"] = fishing.get("water_temp", "--")
        variables["pressure_trend"] = fishing.get("pressure_trend", "--")
        variables["solunar_major"] = fishing.get("solunar_major", "--")
        variables["solunar_minor"] = fishing.get("solunar_minor", "--")
    
    # Parse tides if separate
    tides = raw_data.get("tides", {})
    if tides and "stations" in tides:
        stations = tides.get("stations", [])
        if stations:
            first_station = stations[0]
            if "tide_stage" not in variables or variables["tide_stage"] == "--":
                variables["tide_stage"] = first_station.get("tide_type", "--")
                variables["next_tide_time"] = first_station.get("tide_time", "--")
    
    # Parse forecast summary if available
    forecast = raw_data.get("forecast_5day", {})
    if forecast and "days" in forecast:
        days = forecast.get("days", [])
        if days:
            today = days[0]
            variables["forecast_high"] = today.get("high", "--")
            variables["forecast_low"] = today.get("low", "--")
            variables["forecast_conditions"] = today.get("conditions", "")
    
    return variables


def get_weather_context_for_prompt(weather_data: Optional[Dict]) -> str:
    """
    Format weather data as context for AI prompt.
    
    Args:
        weather_data: Dictionary from fetch_weather_data()
    
    Returns:
        Formatted string to include in AI prompt
    """
    if not weather_data:
        return ""
    
    lines = ["CURRENT CONDITIONS:"]
    
    # Location and time
    if weather_data.get("location"):
        lines.append(f"Location: {weather_data['location']}")
    lines.append(f"Date: {weather_data.get('today_date', 'N/A')} ({weather_data.get('day_of_week', '')})")
    lines.append(f"Time of day: {weather_data.get('time_of_day', 'N/A')}")
    
    # Weather
    if weather_data.get("temperature") and weather_data["temperature"] != "--":
        lines.append(f"Temperature: {weather_data['temperature']}")
    if weather_data.get("conditions"):
        lines.append(f"Conditions: {weather_data['conditions']}")
    if weather_data.get("wind") and weather_data["wind"] != "--":
        lines.append(f"Wind: {weather_data['wind']}")
    if weather_data.get("humidity") and weather_data["humidity"] != "--":
        lines.append(f"Humidity: {weather_data['humidity']}")
    
    # Tides (great for coastal content)
    if weather_data.get("tide_stage") and weather_data["tide_stage"] != "--":
        tide_info = f"Tide: {weather_data['tide_stage']}"
        if weather_data.get("next_tide") and weather_data["next_tide"] != "--":
            tide_info += f" (next {weather_data['next_tide']} at {weather_data.get('next_tide_time', 'N/A')})"
        lines.append(tide_info)
    
    # Moon phase
    if weather_data.get("moon_phase") and weather_data["moon_phase"] != "--":
        lines.append(f"Moon: {weather_data['moon_phase']} ({weather_data.get('moon_illumination', '')})")
    
    # Water temp (for coastal/fishing content)
    if weather_data.get("water_temp") and weather_data["water_temp"] != "--":
        lines.append(f"Water temperature: {weather_data['water_temp']}")
    
    return "\n".join(lines)


# Available template variables for documentation
AVAILABLE_VARIABLES = {
    # System
    "today_date": "Current date (e.g., 'December 11, 2024')",
    "day_of_week": "Day name (e.g., 'Wednesday')",
    "time_of_day": "morning, afternoon, or evening",
    "current_time": "Current time (e.g., '2:45 PM')",
    
    # Weather
    "temperature": "Current temperature (e.g., '72°F')",
    "feels_like": "Feels like temperature",
    "conditions": "Weather conditions (e.g., 'Partly Cloudy')",
    "humidity": "Relative humidity (e.g., '65%')",
    "wind": "Wind speed and direction (e.g., '12 mph SW')",
    "wind_gust": "Wind gust speed",
    "pressure": "Barometric pressure",
    "pressure_trend": "Pressure trend (Rising, Falling, Steady)",
    "uv_index": "UV index",
    "rain_today": "Rainfall today",
    
    # Tides
    "tide_stage": "Current tide stage (Incoming, Outgoing, High Slack, Low Slack)",
    "next_tide": "Next tide event (High tide, Low tide)",
    "next_tide_time": "Time of next tide",
    "tide_height": "Tide height",
    
    # Astronomy
    "moon_phase": "Moon phase name (e.g., 'Waxing Gibbous')",
    "moon_illumination": "Moon illumination percentage",
    "solunar_major": "Next major solunar period",
    "solunar_minor": "Next minor solunar period",
    
    # Water
    "water_temp": "Water temperature",
    
    # Location
    "location": "Location name",
    
    # Forecast
    "forecast_high": "Today's forecast high",
    "forecast_low": "Today's forecast low",
    "forecast_conditions": "Today's forecast conditions",
}


def get_available_variables() -> Dict[str, str]:
    """Return dictionary of available template variables and their descriptions"""
    return AVAILABLE_VARIABLES.copy()
