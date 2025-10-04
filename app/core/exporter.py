"""
Data export functionality for CSV and JSON formats.
"""
import json
import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from app.core.schemas import UnifiedResult


def to_csv(result: UnifiedResult) -> str:
    """Export unified result to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write metadata header
    writer.writerow(["ParadeGuard Weather Analysis Export"])
    writer.writerow(["Generated:", datetime.now().isoformat()])
    writer.writerow(["Location:", result.inputs.place])
    writer.writerow(["Date:", result.inputs.date.strftime("%Y-%m-%d")])
    writer.writerow(["Time Window:", result.inputs.time_window])
    writer.writerow(["Timezone:", result.timezone or "Unknown"])
    writer.writerow([])
    
    # Write geocoding info
    if result.geocode:
        writer.writerow(["Geocoding Information"])
        writer.writerow(["Address", "Latitude", "Longitude"])
        writer.writerow([
            result.geocode.formatted_address,
            result.geocode.lat,
            result.geocode.lon
        ])
        writer.writerow([])
    
    # Write risk assessment
    if result.risk_score:
        writer.writerow(["Risk Assessment"])
        writer.writerow(["Metric", "Score", "Details"])
        writer.writerow([
            "Composite Risk",
            result.risk_score.composite_score,
            f"Confidence: {result.risk_score.confidence}"
        ])
        writer.writerow(["Rain Risk", result.risk_score.rain_score, ""])
        writer.writerow(["Temperature Risk", result.risk_score.temperature_score, ""])
        writer.writerow(["Wind Risk", result.risk_score.wind_score, ""])
        writer.writerow(["Visibility Risk", result.risk_score.visibility_score, ""])
        writer.writerow([])
    
    # Write current conditions
    if result.current_openmeteo:
        writer.writerow(["Current Conditions (Open-Meteo)"])
        writer.writerow(["Metric", "Value", "Unit"])
        current = result.current_openmeteo
        writer.writerow(["Temperature", current.temperature_2m, "°C"])
        writer.writerow(["Apparent Temperature", current.apparent_temperature, "°C"])
        writer.writerow(["Precipitation", current.precipitation, "mm"])
        writer.writerow(["Wind Speed", current.wind_speed_10m, "km/h"])
        writer.writerow(["Wind Direction", current.wind_direction_10m, "degrees"])
        writer.writerow(["Wind Gusts", current.wind_gusts_10m, "km/h"])
        writer.writerow(["Relative Humidity", current.relative_humidity_2m, "%"])
        writer.writerow(["Cloud Cover", current.cloud_cover, "%"])
        writer.writerow(["Weather Code", current.weather_code, ""])
        writer.writerow([])
    
    if result.current_google:
        writer.writerow(["Current Conditions (Google Weather)"])
        writer.writerow(["Metric", "Value", "Unit"])
        current = result.current_google
        writer.writerow(["Temperature", current.temperature, "°C"])
        writer.writerow(["Feels Like", current.feels_like, "°C"])
        writer.writerow(["Precipitation Probability", current.precipitation_probability, "%"])
        writer.writerow(["Precipitation Amount", current.precipitation_mm, "mm"])
        writer.writerow(["Thunderstorm Probability", current.thunderstorm_probability, "%"])
        writer.writerow(["UV Index", current.uv_index, ""])
        writer.writerow(["Visibility", current.visibility, "km"])
        if current.wind:
            writer.writerow(["Wind Speed", current.wind.speed, "km/h"])
            writer.writerow(["Wind Gusts", current.wind.gust, "km/h"])
            writer.writerow(["Wind Direction", current.wind.direction, "degrees"])
        writer.writerow([])
    
    # Write hourly data summary
    if result.hourly:
        writer.writerow(["Hourly Forecast Summary"])
        writer.writerow(["Time", "Temperature", "Apparent Temp", "Precipitation", "Precip Prob", "Wind Speed", "Wind Gusts", "Humidity", "Cloud Cover"])
        
        # Write first 24 hours or all available
        max_hours = min(24, len(result.hourly.time))
        for i in range(max_hours):
            time_str = result.hourly.time[i].strftime("%Y-%m-%d %H:%M") if i < len(result.hourly.time) else ""
            temp = result.hourly.temperature_2m[i] if i < len(result.hourly.temperature_2m) else None
            app_temp = result.hourly.apparent_temperature[i] if i < len(result.hourly.apparent_temperature) else None
            precip = result.hourly.precipitation[i] if i < len(result.hourly.precipitation) else None
            precip_prob = result.hourly.precipitation_probability[i] if i < len(result.hourly.precipitation_probability) else None
            wind_speed = result.hourly.wind_speed_10m[i] if i < len(result.hourly.wind_speed_10m) else None
            wind_gusts = result.hourly.wind_gusts_10m[i] if i < len(result.hourly.wind_gusts_10m) else None
            humidity = result.hourly.relative_humidity_2m[i] if i < len(result.hourly.relative_humidity_2m) else None
            cloud = result.hourly.cloud_cover[i] if i < len(result.hourly.cloud_cover) else None
            
            writer.writerow([time_str, temp, app_temp, precip, precip_prob, wind_speed, wind_gusts, humidity, cloud])
        writer.writerow([])
    
    # Write daily data summary
    if result.daily:
        writer.writerow(["Daily Forecast Summary"])
        writer.writerow(["Date", "Max Temp", "Min Temp", "Precip Sum", "Rain Sum", "Precip Hours", "Max Wind Speed", "Max Wind Gusts", "UV Index Max"])
        
        # Write first 7 days or all available
        max_days = min(7, len(result.daily.time))
        for i in range(max_days):
            date_str = result.daily.time[i].strftime("%Y-%m-%d") if i < len(result.daily.time) else ""
            max_temp = result.daily.temperature_2m_max[i] if i < len(result.daily.temperature_2m_max) else None
            min_temp = result.daily.temperature_2m_min[i] if i < len(result.daily.temperature_2m_min) else None
            precip_sum = result.daily.precipitation_sum[i] if i < len(result.daily.precipitation_sum) else None
            rain_sum = result.daily.rain_sum[i] if i < len(result.daily.rain_sum) else None
            precip_hours = result.daily.precipitation_hours[i] if i < len(result.daily.precipitation_hours) else None
            max_wind = result.daily.wind_speed_10m_max[i] if i < len(result.daily.wind_speed_10m_max) else None
            max_gusts = result.daily.wind_gusts_10m_max[i] if i < len(result.daily.wind_gusts_10m_max) else None
            uv_max = result.daily.uv_index_max[i] if i < len(result.daily.uv_index_max) else None
            
            writer.writerow([date_str, max_temp, min_temp, precip_sum, rain_sum, precip_hours, max_wind, max_gusts, uv_max])
        writer.writerow([])
    
    # Write historical context
    if result.historical:
        writer.writerow(["Historical Context (Meteostat)"])
        writer.writerow(["Month Percentile Rain", result.historical.month_percentile_rain, "%"])
        writer.writerow(["Month Percentile Temperature", result.historical.month_percentile_temp, "%"])
        writer.writerow([])
    
    # Write notes
    if result.notes:
        writer.writerow(["Notes"])
        for note in result.notes:
            writer.writerow([note])
        writer.writerow([])
    
    # Write data sources
    writer.writerow(["Data Sources"])
    writer.writerow(["Google Geocoding API"])
    writer.writerow(["Google Weather API"])
    writer.writerow(["Meteostat API (via RapidAPI)"])
    writer.writerow(["Open-Meteo API"])
    writer.writerow([])
    writer.writerow(["Attribution"])
    writer.writerow(["WMO weather codes provided by Open-Meteo"])
    writer.writerow(["See README.md for full license information"])
    
    return output.getvalue()


def to_json(result: UnifiedResult) -> str:
    """Export unified result to JSON format."""
    export_data = {
        "metadata": {
            "export_timestamp": datetime.now().isoformat(),
            "app_version": "1.0.0",
            "data_sources": [
                "Google Geocoding API",
                "Google Weather API", 
                "Meteostat API (via RapidAPI)",
                "Open-Meteo API"
            ],
            "attribution": "WMO weather codes provided by Open-Meteo"
        },
        "query": {
            "place": result.inputs.place,
            "date": result.inputs.date.isoformat(),
            "time_window": result.inputs.time_window,
            "timezone": result.timezone
        },
        "geocoding": None,
        "current_conditions": {
            "openmeteo": None,
            "google": None
        },
        "forecast": {
            "hourly": None,
            "daily": None
        },
        "historical": None,
        "risk_assessment": None,
        "notes": result.notes
    }
    
    # Add geocoding data
    if result.geocode:
        export_data["geocoding"] = {
            "address": result.geocode.address,
            "formatted_address": result.geocode.formatted_address,
            "latitude": result.geocode.lat,
            "longitude": result.geocode.lon
        }
    
    # Add current conditions
    if result.current_openmeteo:
        export_data["current_conditions"]["openmeteo"] = {
            "time": result.current_openmeteo.time.isoformat() if result.current_openmeteo.time else None,
            "temperature_2m": result.current_openmeteo.temperature_2m,
            "apparent_temperature": result.current_openmeteo.apparent_temperature,
            "precipitation": result.current_openmeteo.precipitation,
            "wind_speed_10m": result.current_openmeteo.wind_speed_10m,
            "wind_direction_10m": result.current_openmeteo.wind_direction_10m,
            "wind_gusts_10m": result.current_openmeteo.wind_gusts_10m,
            "relative_humidity_2m": result.current_openmeteo.relative_humidity_2m,
            "cloud_cover": result.current_openmeteo.cloud_cover,
            "weather_code": result.current_openmeteo.weather_code,
            "is_day": result.current_openmeteo.is_day
        }
    
    if result.current_google:
        export_data["current_conditions"]["google"] = {
            "time": result.current_google.time.isoformat() if result.current_google.time else None,
            "temperature": result.current_google.temperature,
            "feels_like": result.current_google.feels_like,
            "dew_point": result.current_google.dew_point,
            "relative_humidity": result.current_google.relative_humidity,
            "uv_index": result.current_google.uv_index,
            "precipitation_probability": result.current_google.precipitation_probability,
            "precipitation_mm": result.current_google.precipitation_mm,
            "thunderstorm_probability": result.current_google.thunderstorm_probability,
            "visibility": result.current_google.visibility,
            "cloud_cover": result.current_google.cloud_cover,
            "condition": result.current_google.condition,
            "wind": {
                "speed": result.current_google.wind.speed if result.current_google.wind else None,
                "gust": result.current_google.wind.gust if result.current_google.wind else None,
                "direction": result.current_google.wind.direction if result.current_google.wind else None
            } if result.current_google.wind else None
        }
    
    # Add forecast data
    if result.hourly:
        export_data["forecast"]["hourly"] = {
            "time": [t.isoformat() for t in result.hourly.time],
            "temperature_2m": result.hourly.temperature_2m,
            "apparent_temperature": result.hourly.apparent_temperature,
            "precipitation": result.hourly.precipitation,
            "precipitation_probability": result.hourly.precipitation_probability,
            "weather_code": result.hourly.weather_code,
            "wind_speed_10m": result.hourly.wind_speed_10m,
            "wind_direction_10m": result.hourly.wind_direction_10m,
            "wind_gusts_10m": result.hourly.wind_gusts_10m,
            "relative_humidity_2m": result.hourly.relative_humidity_2m,
            "cloud_cover": result.hourly.cloud_cover,
            "dew_point_2m": result.hourly.dew_point_2m,
            "is_day": result.hourly.is_day,
            "visibility": result.hourly.visibility
        }
    
    if result.daily:
        export_data["forecast"]["daily"] = {
            "time": [t.isoformat() for t in result.daily.time],
            "weather_code": result.daily.weather_code,
            "temperature_2m_max": result.daily.temperature_2m_max,
            "temperature_2m_min": result.daily.temperature_2m_min,
            "apparent_temperature_max": result.daily.apparent_temperature_max,
            "apparent_temperature_min": result.daily.apparent_temperature_min,
            "precipitation_sum": result.daily.precipitation_sum,
            "rain_sum": result.daily.rain_sum,
            "precipitation_hours": result.daily.precipitation_hours,
            "precipitation_probability_max": result.daily.precipitation_probability_max,
            "wind_speed_10m_max": result.daily.wind_speed_10m_max,
            "wind_gusts_10m_max": result.daily.wind_gusts_10m_max,
            "wind_direction_10m_dominant": result.daily.wind_direction_10m_dominant,
            "shortwave_radiation_sum": result.daily.shortwave_radiation_sum,
            "uv_index_max": result.daily.uv_index_max,
            "sunrise": [t.isoformat() if t else None for t in result.daily.sunrise],
            "sunset": [t.isoformat() if t else None for t in result.daily.sunset],
            "daylight_duration": result.daily.daylight_duration
        }
    
    # Add historical data
    if result.historical:
        export_data["historical"] = {
            "month_percentile_rain": result.historical.month_percentile_rain,
            "month_percentile_temp": result.historical.month_percentile_temp,
            "monthly_data": [
                {
                    "date": row.date,
                    "tavg": row.tavg,
                    "tmin": row.tmin,
                    "tmax": row.tmax,
                    "prcp": row.prcp,
                    "tsun": row.tsun,
                    "pres": row.pres
                }
                for row in result.historical.data
            ]
        }
    
    # Add risk assessment
    if result.risk_score:
        export_data["risk_assessment"] = {
            "composite_score": result.risk_score.composite_score,
            "rain_score": result.risk_score.rain_score,
            "temperature_score": result.risk_score.temperature_score,
            "wind_score": result.risk_score.wind_score,
            "visibility_score": result.risk_score.visibility_score,
            "confidence": result.risk_score.confidence,
            "confidence_value": result.risk_score.confidence_value
        }
    
    return json.dumps(export_data, indent=2, ensure_ascii=False)


def get_export_filename(result: UnifiedResult, format_type: str) -> str:
    """Generate filename for export."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    place_safe = "".join(c for c in result.inputs.place if c.isalnum() or c in (' ', '-', '_')).rstrip()
    place_safe = place_safe.replace(' ', '_')[:20]  # Limit length
    
    return f"paradeguard_{place_safe}_{result.inputs.date.strftime('%Y%m%d')}_{timestamp}.{format_type}"
