"""
Pydantic models for API inputs and outputs.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GeocodeResult(BaseModel):
    """Result from Google Geocoding API."""
    address: str
    lat: float
    lon: float
    formatted_address: str


class WindData(BaseModel):
    """Wind information."""
    speed: Optional[float] = None  # km/h
    gust: Optional[float] = None   # km/h
    direction: Optional[int] = None  # degrees


class GoogleWeatherCurrent(BaseModel):
    """Current conditions from Google Weather API."""
    time: Optional[datetime] = None
    is_day: Optional[bool] = None
    condition: Optional[str] = None
    temperature: Optional[float] = None  # °C
    feels_like: Optional[float] = None   # °C
    dew_point: Optional[float] = None    # °C
    relative_humidity: Optional[float] = None  # %
    uv_index: Optional[float] = None
    precipitation_probability: Optional[float] = None  # %
    precipitation_mm: Optional[float] = None  # mm
    thunderstorm_probability: Optional[float] = None  # %
    wind: Optional[WindData] = None
    visibility: Optional[float] = None  # km
    cloud_cover: Optional[float] = None  # %


class MeteostatMonthlyRow(BaseModel):
    """Monthly climatology data from Meteostat."""
    date: str  # YYYY-MM-DD
    tavg: Optional[float] = None  # °C
    tmin: Optional[float] = None  # °C
    tmax: Optional[float] = None  # °C
    prcp: Optional[float] = None  # mm
    tsun: Optional[float] = None  # hours
    pres: Optional[float] = None  # hPa


class MeteostatData(BaseModel):
    """Meteostat monthly data."""
    data: List[MeteostatMonthlyRow]
    month_percentile_rain: Optional[float] = None
    month_percentile_temp: Optional[float] = None


class OpenMeteoCurrent(BaseModel):
    """Current conditions from Open-Meteo."""
    time: Optional[datetime] = None
    temperature_2m: Optional[float] = None  # °C
    apparent_temperature: Optional[float] = None  # °C
    precipitation: Optional[float] = None  # mm
    wind_speed_10m: Optional[float] = None  # km/h
    wind_direction_10m: Optional[int] = None  # degrees
    wind_gusts_10m: Optional[float] = None  # km/h
    relative_humidity_2m: Optional[float] = None  # %
    cloud_cover: Optional[float] = None  # %
    weather_code: Optional[int] = None
    is_day: Optional[bool] = None


class OpenMeteoHourly(BaseModel):
    """Hourly forecast data from Open-Meteo."""
    time: List[datetime]
    temperature_2m: List[Optional[float]]
    apparent_temperature: List[Optional[float]]
    precipitation: List[Optional[float]]
    precipitation_probability: List[Optional[float]]
    weather_code: List[Optional[int]]
    wind_speed_10m: List[Optional[float]]
    wind_direction_10m: List[Optional[int]]
    wind_gusts_10m: List[Optional[float]]
    relative_humidity_2m: List[Optional[float]]
    cloud_cover: List[Optional[float]]
    dew_point_2m: List[Optional[float]]
    is_day: List[Optional[bool]]
    visibility: List[Optional[float]]


class OpenMeteoDaily(BaseModel):
    """Daily forecast data from Open-Meteo."""
    time: List[datetime]
    weather_code: List[Optional[int]]
    temperature_2m_max: List[Optional[float]]
    temperature_2m_min: List[Optional[float]]
    apparent_temperature_max: List[Optional[float]]
    apparent_temperature_min: List[Optional[float]]
    precipitation_sum: List[Optional[float]]
    rain_sum: List[Optional[float]]
    precipitation_hours: List[Optional[float]]
    precipitation_probability_max: List[Optional[float]]
    wind_speed_10m_max: List[Optional[float]]
    wind_gusts_10m_max: List[Optional[float]]
    wind_direction_10m_dominant: List[Optional[int]]
    shortwave_radiation_sum: List[Optional[float]]
    uv_index_max: List[Optional[float]]
    sunrise: List[Optional[datetime]]
    sunset: List[Optional[datetime]]
    daylight_duration: List[Optional[float]]


class RiskScore(BaseModel):
    """Risk assessment results."""
    composite_score: float  # 0-100
    rain_score: float
    temperature_score: float
    wind_score: float
    visibility_score: float
    confidence: str  # Low/Medium/High
    confidence_value: float  # 0-1


class QueryInputs(BaseModel):
    """User query inputs."""
    place: str
    date: datetime
    time_window: str  # Morning/Afternoon/Evening/Night
    date_range: Optional[tuple] = None


class UnifiedResult(BaseModel):
    """Combined result from all services."""
    inputs: QueryInputs
    geocode: Optional[GeocodeResult] = None
    current_google: Optional[GoogleWeatherCurrent] = None
    current_openmeteo: Optional[OpenMeteoCurrent] = None
    hourly: Optional[OpenMeteoHourly] = None
    daily: Optional[OpenMeteoDaily] = None
    historical: Optional[MeteostatData] = None
    risk_score: Optional[RiskScore] = None
    timezone: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
