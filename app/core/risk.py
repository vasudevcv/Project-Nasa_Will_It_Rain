"""
Risk scoring algorithm for weather conditions.
"""
from typing import List, Optional, Dict, Any
import numpy as np
from app.core.schemas import RiskScore, OpenMeteoHourly, OpenMeteoCurrent, GoogleWeatherCurrent


# Risk weights
RAIN_WEIGHT = 0.40
TEMPERATURE_WEIGHT = 0.25
WIND_WEIGHT = 0.20
VISIBILITY_WEIGHT = 0.15

# Rain thresholds
DRIZZLE_THRESHOLD = 0.2  # mm/h
RAIN_THRESHOLD = 1.0     # mm/h
HEAVY_RAIN_THRESHOLD = 4.0  # mm/h
ELEVATED_PROB_THRESHOLD = 50  # %
HIGH_PROB_THRESHOLD = 70     # %

# Temperature thresholds (apparent temperature)
COOL_THRESHOLD = 18  # °C
HOT_THRESHOLD = 32   # °C

# Wind thresholds
GUST_CAUTION_THRESHOLD = 35  # km/h
GUST_HIGH_THRESHOLD = 55     # km/h

# Visibility thresholds
CLOUD_HIGH_THRESHOLD = 80  # %
UV_HIGH_THRESHOLD = 7      # UV index


def calculate_rain_score(
    precipitation: List[Optional[float]], 
    precipitation_prob: List[Optional[float]],
    is_day: List[Optional[bool]] = None
) -> float:
    """Calculate rain risk score (0-100)."""
    if not precipitation or not precipitation_prob:
        return 0.0
    
    # Filter out None values
    valid_precip = [p for p in precipitation if p is not None]
    valid_prob = [p for p in precipitation_prob if p is not None]
    
    if not valid_precip or not valid_prob:
        return 0.0
    
    # Calculate intensity score
    max_precip = max(valid_precip)
    intensity_score = 0.0
    
    if max_precip >= HEAVY_RAIN_THRESHOLD:
        intensity_score = 100
    elif max_precip >= RAIN_THRESHOLD:
        intensity_score = 70
    elif max_precip >= DRIZZLE_THRESHOLD:
        intensity_score = 40
    else:
        intensity_score = 0
    
    # Calculate probability score
    max_prob = max(valid_prob)
    prob_score = 0.0
    
    if max_prob >= HIGH_PROB_THRESHOLD:
        prob_score = 100
    elif max_prob >= ELEVATED_PROB_THRESHOLD:
        prob_score = 60
    else:
        prob_score = max_prob * 0.6  # Scale 0-50% to 0-30 points
    
    # Combine intensity and probability (weighted average)
    rain_score = (intensity_score * 0.6) + (prob_score * 0.4)
    
    return min(rain_score, 100.0)


def calculate_temperature_score(
    apparent_temps: List[Optional[float]],
    is_day: List[Optional[bool]] = None
) -> float:
    """Calculate temperature comfort score (0-100)."""
    if not apparent_temps:
        return 0.0
    
    # Filter out None values
    valid_temps = [t for t in apparent_temps if t is not None]
    
    if not valid_temps:
        return 0.0
    
    # Calculate comfort score based on apparent temperature
    min_temp = min(valid_temps)
    max_temp = max(valid_temps)
    avg_temp = sum(valid_temps) / len(valid_temps)
    
    temp_score = 0.0
    
    # Cold discomfort
    if min_temp < COOL_THRESHOLD:
        cold_discomfort = (COOL_THRESHOLD - min_temp) * 5  # 5 points per degree below threshold
        temp_score += min(cold_discomfort, 50)  # Cap at 50 points
    
    # Hot discomfort
    if max_temp > HOT_THRESHOLD:
        hot_discomfort = (max_temp - HOT_THRESHOLD) * 5  # 5 points per degree above threshold
        temp_score += min(hot_discomfort, 50)  # Cap at 50 points
    
    return min(temp_score, 100.0)


def calculate_wind_score(
    wind_speeds: List[Optional[float]], 
    wind_gusts: List[Optional[float]]
) -> float:
    """Calculate wind risk score (0-100)."""
    if not wind_speeds and not wind_gusts:
        return 0.0
    
    wind_score = 0.0
    
    # Wind speed contribution
    if wind_speeds:
        valid_speeds = [w for w in wind_speeds if w is not None]
        if valid_speeds:
            max_speed = max(valid_speeds)
            if max_speed > 30:  # km/h
                wind_score += min((max_speed - 30) * 2, 40)  # Up to 40 points
    
    # Wind gust contribution (more important)
    if wind_gusts:
        valid_gusts = [g for g in wind_gusts if g is not None]
        if valid_gusts:
            max_gust = max(valid_gusts)
            if max_gust >= GUST_HIGH_THRESHOLD:
                wind_score += 60
            elif max_gust >= GUST_CAUTION_THRESHOLD:
                wind_score += 40
            else:
                wind_score += min(max_gust * 0.8, 30)  # Up to 30 points
    
    return min(wind_score, 100.0)


def calculate_visibility_score(
    cloud_cover: List[Optional[float]], 
    visibility: List[Optional[float]] = None,
    uv_index: List[Optional[float]] = None,
    is_day: List[Optional[bool]] = None
) -> float:
    """Calculate visibility/sky condition score (0-100)."""
    visibility_score = 0.0
    
    # Cloud cover contribution
    if cloud_cover:
        valid_cloud = [c for c in cloud_cover if c is not None]
        if valid_cloud:
            avg_cloud = sum(valid_cloud) / len(valid_cloud)
            if avg_cloud > CLOUD_HIGH_THRESHOLD:
                visibility_score += 50  # Heavy cloud cover
            elif avg_cloud > 60:
                visibility_score += 30  # Moderate cloud cover
    
    # Visibility contribution
    if visibility:
        valid_visibility = [v for v in visibility if v is not None]
        if valid_visibility:
            min_visibility = min(valid_visibility)
            if min_visibility < 5:  # km
                visibility_score += 40  # Poor visibility
            elif min_visibility < 10:
                visibility_score += 20  # Reduced visibility
    
    # UV index contribution (daytime only)
    if uv_index and is_day:
        valid_uv = [u for u in uv_index if u is not None]
        valid_day = [d for d in is_day if d is not None]
        
        if valid_uv and valid_day:
            # Only consider UV during daytime
            day_uv = [uv for uv, day in zip(valid_uv, valid_day) if day and uv is not None]
            if day_uv:
                max_uv = max(day_uv)
                if max_uv >= UV_HIGH_THRESHOLD:
                    visibility_score += 30  # High UV exposure
    
    return min(visibility_score, 100.0)


def calculate_confidence(
    hourly_data: Optional[OpenMeteoHourly],
    current_data: Optional[OpenMeteoCurrent] = None,
    google_data: Optional[GoogleWeatherCurrent] = None
) -> tuple[str, float]:
    """Calculate confidence level and value."""
    confidence_factors = []
    
    # Data completeness factor
    if hourly_data:
        total_fields = 0
        complete_fields = 0
        
        # Check key fields for completeness
        key_fields = [
            hourly_data.temperature_2m,
            hourly_data.precipitation,
            hourly_data.precipitation_probability,
            hourly_data.wind_speed_10m
        ]
        
        for field in key_fields:
            if field:
                total_fields += 1
                non_none_count = sum(1 for x in field if x is not None)
                if non_none_count > 0:
                    complete_fields += 1
        
        if total_fields > 0:
            completeness = complete_fields / total_fields
            confidence_factors.append(completeness)
    
    # Model agreement factor (if we have multiple data sources)
    if current_data and google_data:
        # Simple agreement check on temperature
        if (current_data.temperature_2m is not None and 
            google_data.temperature is not None):
            temp_diff = abs(current_data.temperature_2m - google_data.temperature)
            if temp_diff < 2.0:  # Within 2°C
                confidence_factors.append(0.8)
            elif temp_diff < 5.0:  # Within 5°C
                confidence_factors.append(0.6)
            else:
                confidence_factors.append(0.3)
    
    # Time proximity factor (closer to current time = higher confidence)
    confidence_factors.append(0.7)  # Default moderate confidence
    
    # Calculate overall confidence
    if confidence_factors:
        confidence_value = sum(confidence_factors) / len(confidence_factors)
    else:
        confidence_value = 0.5
    
    # Convert to confidence level
    if confidence_value >= 0.8:
        confidence_level = "High"
    elif confidence_value >= 0.6:
        confidence_level = "Medium"
    else:
        confidence_level = "Low"
    
    return confidence_level, confidence_value


def calculate_composite_risk_score(
    hourly_data: Optional[OpenMeteoHourly],
    current_data: Optional[OpenMeteoCurrent] = None,
    google_data: Optional[GoogleWeatherCurrent] = None
) -> RiskScore:
    """Calculate composite risk score from all factors."""
    
    # Initialize scores
    rain_score = 0.0
    temp_score = 0.0
    wind_score = 0.0
    visibility_score = 0.0
    
    if hourly_data:
        # Calculate individual scores
        rain_score = calculate_rain_score(
            hourly_data.precipitation or [],
            hourly_data.precipitation_probability or [],
            hourly_data.is_day
        )
        
        temp_score = calculate_temperature_score(
            hourly_data.apparent_temperature or [],
            hourly_data.is_day
        )
        
        wind_score = calculate_wind_score(
            hourly_data.wind_speed_10m or [],
            hourly_data.wind_gusts_10m or []
        )
        
        visibility_score = calculate_visibility_score(
            hourly_data.cloud_cover or [],
            hourly_data.visibility,
            # UV index not available in hourly data, would need daily data
            None,
            hourly_data.is_day
        )
    
    # Calculate weighted composite score
    composite_score = (
        rain_score * RAIN_WEIGHT +
        temp_score * TEMPERATURE_WEIGHT +
        wind_score * WIND_WEIGHT +
        visibility_score * VISIBILITY_WEIGHT
    )
    
    # Calculate confidence
    confidence_level, confidence_value = calculate_confidence(
        hourly_data, current_data, google_data
    )
    
    return RiskScore(
        composite_score=round(composite_score, 1),
        rain_score=round(rain_score, 1),
        temperature_score=round(temp_score, 1),
        wind_score=round(wind_score, 1),
        visibility_score=round(visibility_score, 1),
        confidence=confidence_level,
        confidence_value=round(confidence_value, 2)
    )


def get_risk_band(score: float) -> tuple[str, str]:
    """Get risk band and color for a score."""
    if score >= 80:
        return "Very High", "red"
    elif score >= 60:
        return "High", "orange"
    elif score >= 40:
        return "Moderate", "yellow"
    elif score >= 20:
        return "Low", "lightgreen"
    else:
        return "Very Low", "green"


def get_risk_verdict(score: float, time_window: str) -> str:
    """Generate a plain language verdict."""
    band, _ = get_risk_band(score)
    
    if score >= 70:
        return f"High risk of weather disruption during {time_window}"
    elif score >= 50:
        return f"Moderate weather risk during {time_window}"
    elif score >= 30:
        return f"Some weather concerns during {time_window}"
    else:
        return f"Good weather conditions expected during {time_window}"
