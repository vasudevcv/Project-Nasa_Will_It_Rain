"""
Google Weather API service for current conditions.
"""
import httpx
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional
from datetime import datetime
import logging

from app.core.schemas import GoogleWeatherCurrent, WindData
from app.core.config import get_api_key

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
)
@st.cache_data(ttl=900, show_spinner=False)  # Cache for 15 minutes
def get_current_weather(lat: float, lon: float) -> Optional[GoogleWeatherCurrent]:
    """
    Get current weather conditions from Google Weather API.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        GoogleWeatherCurrent with current conditions
        None if error occurred
    """
    try:
        api_key = get_api_key("GOOGLE_WEATHER_API_KEY")
        
        url = "https://weather.googleapis.com/v1/currentConditions:lookup"
        
        payload = {
            "location": {
                "latitude": lat,
                "longitude": lon
            },
            "key": api_key
        }
        
        logger.info(f"Fetching current weather for {lat}, {lon}")
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the response
            current = data.get("currentConditions", {})
            
            # Parse wind data
            wind_info = current.get("wind", {})
            wind_data = None
            if wind_info:
                wind_data = WindData(
                    speed=wind_info.get("speed"),
                    gust=wind_info.get("gust"),
                    direction=wind_info.get("direction")
                )
            
            # Parse precipitation data
            precipitation = current.get("precipitation", {})
            precipitation_prob = precipitation.get("probability", {}).get("percent")
            precipitation_mm = precipitation.get("qpf", {}).get("quantity")
            
            weather_result = GoogleWeatherCurrent(
                time=datetime.now(),  # Google doesn't always provide timestamp
                is_day=current.get("isDay"),
                condition=current.get("weatherCondition", {}).get("type"),
                temperature=current.get("temperature"),
                feels_like=current.get("feelsLike"),
                dew_point=current.get("dewPoint"),
                relative_humidity=current.get("rh"),
                uv_index=current.get("uvIndex"),
                precipitation_probability=precipitation_prob,
                precipitation_mm=precipitation_mm,
                thunderstorm_probability=current.get("thunderstormProbability"),
                wind=wind_data,
                visibility=current.get("visibility"),
                cloud_cover=current.get("cloudCover")
            )
            
            logger.info("Successfully fetched current weather from Google")
            return weather_result
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during weather fetch: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error during weather fetch: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during weather fetch: {e}")
        return None


def validate_weather_result(result: Optional[GoogleWeatherCurrent]) -> tuple[bool, str]:
    """
    Validate a weather result.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if result is None:
        return False, "Unable to fetch current weather conditions."
    
    # Check if we have at least some basic data
    if (result.temperature is None and 
        result.precipitation_probability is None and 
        result.wind is None):
        return False, "Insufficient weather data available."
    
    return True, ""
