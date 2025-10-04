"""
Open-Meteo API service for forecast and timeseries data.
"""
import httpx
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional, List
from datetime import datetime, date
import logging

from app.core.schemas import OpenMeteoCurrent, OpenMeteoHourly, OpenMeteoDaily

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
)
@st.cache_data(ttl=900, show_spinner=False)  # Cache for 15 minutes
def get_forecast_data(
    lat: float, 
    lon: float, 
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> tuple[Optional[OpenMeteoCurrent], Optional[OpenMeteoHourly], Optional[OpenMeteoDaily]]:
    """
    Get forecast data from Open-Meteo API.
    
    Args:
        lat: Latitude
        lon: Longitude
        start_date: Optional start date for forecast
        end_date: Optional end date for forecast
        
    Returns:
        Tuple of (current, hourly, daily) data
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "timezone": "auto",
            "current": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m,relative_humidity_2m,cloud_cover,weather_code,is_day",
            "hourly": "temperature_2m,apparent_temperature,precipitation,precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,relative_humidity_2m,cloud_cover,dew_point_2m,is_day,visibility",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_sum,rain_sum,precipitation_hours,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant,shortwave_radiation_sum,uv_index_max,sunrise,sunset,daylight_duration"
        }
        
        # Add date range if provided
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        logger.info(f"Fetching forecast data for {lat}, {lon}")
        
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse current conditions
            current_data = data.get("current", {})
            current = None
            if current_data:
                current = OpenMeteoCurrent(
                    time=datetime.fromisoformat(current_data.get("time", "").replace("Z", "+00:00")) if current_data.get("time") else None,
                    temperature_2m=current_data.get("temperature_2m"),
                    apparent_temperature=current_data.get("apparent_temperature"),
                    precipitation=current_data.get("precipitation"),
                    wind_speed_10m=current_data.get("wind_speed_10m"),
                    wind_direction_10m=current_data.get("wind_direction_10m"),
                    wind_gusts_10m=current_data.get("wind_gusts_10m"),
                    relative_humidity_2m=current_data.get("relative_humidity_2m"),
                    cloud_cover=current_data.get("cloud_cover"),
                    weather_code=current_data.get("weather_code"),
                    is_day=current_data.get("is_day"),
                    surface_pressure=None,  # Not requested in simplified version
                    dew_point_2m=None,  # Not requested in simplified version
                    visibility=None  # Not requested in simplified version
                )
            
            # Parse hourly data
            hourly_data = data.get("hourly", {})
            hourly = None
            if hourly_data:
                # Parse time series
                times = []
                if hourly_data.get("time"):
                    for time_str in hourly_data["time"]:
                        try:
                            times.append(datetime.fromisoformat(time_str.replace("Z", "+00:00")))
                        except ValueError:
                            times.append(None)
                
                hourly = OpenMeteoHourly(
                    time=times,
                    temperature_2m=hourly_data.get("temperature_2m", []),
                    apparent_temperature=hourly_data.get("apparent_temperature", []),
                    precipitation=hourly_data.get("precipitation", []),
                    precipitation_probability=hourly_data.get("precipitation_probability", []),
                    weather_code=hourly_data.get("weather_code", []),
                    wind_speed_10m=hourly_data.get("wind_speed_10m", []),
                    wind_direction_10m=hourly_data.get("wind_direction_10m", []),
                    wind_gusts_10m=hourly_data.get("wind_gusts_10m", []),
                    relative_humidity_2m=hourly_data.get("relative_humidity_2m", []),
                    cloud_cover=hourly_data.get("cloud_cover", []),
                    dew_point_2m=hourly_data.get("dew_point_2m", []),
                    is_day=hourly_data.get("is_day", []),
                    visibility=hourly_data.get("visibility", []),
                    surface_pressure=[],  # Not requested in simplified version
                    pressure_msl=[],  # Not requested in simplified version
                    cloud_cover_low=[],  # Not requested in simplified version
                    cloud_cover_mid=[],  # Not requested in simplified version
                    cloud_cover_high=[],  # Not requested in simplified version
                    rain=[],  # Not requested in simplified version
                    showers=[],  # Not requested in simplified version
                    snowfall=[],  # Not requested in simplified version
                    evapotranspiration=[],  # Not requested in simplified version
                    et0_fao_evapotranspiration=[],  # Not requested in simplified version
                    vapour_pressure_deficit=[]  # Not requested in simplified version
                )
            
            # Parse daily data
            daily_data = data.get("daily", {})
            daily = None
            if daily_data:
                # Parse time series
                times = []
                if daily_data.get("time"):
                    for time_str in daily_data["time"]:
                        try:
                            times.append(datetime.fromisoformat(time_str.replace("Z", "+00:00")))
                        except ValueError:
                            times.append(None)
                
                # Parse sunrise/sunset times
                sunrise_times = []
                sunset_times = []
                if daily_data.get("sunrise"):
                    for time_str in daily_data["sunrise"]:
                        try:
                            sunrise_times.append(datetime.fromisoformat(time_str.replace("Z", "+00:00")))
                        except ValueError:
                            sunrise_times.append(None)
                if daily_data.get("sunset"):
                    for time_str in daily_data["sunset"]:
                        try:
                            sunset_times.append(datetime.fromisoformat(time_str.replace("Z", "+00:00")))
                        except ValueError:
                            sunset_times.append(None)
                
                daily = OpenMeteoDaily(
                    time=times,
                    weather_code=daily_data.get("weather_code", []),
                    temperature_2m_max=daily_data.get("temperature_2m_max", []),
                    temperature_2m_min=daily_data.get("temperature_2m_min", []),
                    apparent_temperature_max=daily_data.get("apparent_temperature_max", []),
                    apparent_temperature_min=daily_data.get("apparent_temperature_min", []),
                    precipitation_sum=daily_data.get("precipitation_sum", []),
                    rain_sum=daily_data.get("rain_sum", []),
                    showers_sum=[],  # Not requested in simplified version
                    snowfall_sum=[],  # Not requested in simplified version
                    precipitation_hours=daily_data.get("precipitation_hours", []),
                    precipitation_probability_max=daily_data.get("precipitation_probability_max", []),
                    wind_speed_10m_max=daily_data.get("wind_speed_10m_max", []),
                    wind_gusts_10m_max=daily_data.get("wind_gusts_10m_max", []),
                    wind_direction_10m_dominant=daily_data.get("wind_direction_10m_dominant", []),
                    shortwave_radiation_sum=daily_data.get("shortwave_radiation_sum", []),
                    uv_index_max=daily_data.get("uv_index_max", []),
                    sunrise=sunrise_times,
                    sunset=sunset_times,
                    daylight_duration=daily_data.get("daylight_duration", []),
                    surface_pressure_max=[],  # Not requested in simplified version
                    surface_pressure_min=[],  # Not requested in simplified version
                    pressure_msl_max=[],  # Not requested in simplified version
                    pressure_msl_min=[],  # Not requested in simplified version
                    cloud_cover_max=[],  # Not requested in simplified version
                    cloud_cover_low_max=[],  # Not requested in simplified version
                    cloud_cover_mid_max=[],  # Not requested in simplified version
                    cloud_cover_high_max=[],  # Not requested in simplified version
                    evapotranspiration_sum=[],  # Not requested in simplified version
                    et0_fao_evapotranspiration_sum=[],  # Not requested in simplified version
                    vapour_pressure_deficit_max=[]  # Not requested in simplified version
                )
            
            logger.info("Successfully fetched forecast data from Open-Meteo")
            return current, hourly, daily
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during Open-Meteo fetch: {e.response.status_code}")
        return None, None, None
    except httpx.RequestError as e:
        logger.error(f"Request error during Open-Meteo fetch: {e}")
        return None, None, None
    except Exception as e:
        logger.error(f"Unexpected error during Open-Meteo fetch: {e}")
        return None, None, None


def validate_forecast_data(
    current: Optional[OpenMeteoCurrent], 
    hourly: Optional[OpenMeteoHourly], 
    daily: Optional[OpenMeteoDaily]
) -> tuple[bool, str]:
    """
    Validate forecast data.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not current and not hourly and not daily:
        return False, "Unable to fetch forecast data."
    
    if hourly and not hourly.time:
        return False, "Invalid hourly forecast data."
    
    if daily and not daily.time:
        return False, "Invalid daily forecast data."
    
    return True, ""


def get_timezone_from_forecast(lat: float, lon: float) -> str:
    """
    Get timezone from Open-Meteo API.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Timezone string
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "timezone": "auto",
            "current": "temperature_2m"
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("timezone", "UTC")
            
    except Exception as e:
        logger.error(f"Error fetching timezone: {e}")
        return "UTC"
