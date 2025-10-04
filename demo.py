#!/usr/bin/env python3
"""
ParadeGuard Demo Script
Shows how the application would work with sample data.
"""
import json
from datetime import datetime, date, timedelta

def create_sample_data():
    """Create sample data to demonstrate the app functionality."""
    
    # Sample geocoding result
    geocode_data = {
        "address": "Pathanamthitta, Kerala",
        "formatted_address": "Pathanamthitta, Kerala, India",
        "latitude": 9.2647,
        "longitude": 76.7870
    }
    
    # Sample weather data
    weather_data = {
        "current_conditions": {
            "temperature": 28.5,
            "feels_like": 32.1,
            "precipitation_probability": 45,
            "precipitation_mm": 0.2,
            "wind_speed": 12.3,
            "wind_gusts": 18.7,
            "humidity": 78,
            "cloud_cover": 65,
            "uv_index": 6
        },
        "hourly_forecast": [
            {"time": "2024-05-21T18:00:00", "temp": 28.5, "precip": 0.2, "precip_prob": 45, "wind": 12.3},
            {"time": "2024-05-21T19:00:00", "temp": 27.8, "precip": 0.8, "precip_prob": 65, "wind": 15.2},
            {"time": "2024-05-21T20:00:00", "temp": 27.2, "precip": 1.2, "precip_prob": 75, "wind": 18.1},
            {"time": "2024-05-21T21:00:00", "temp": 26.9, "precip": 0.5, "precip_prob": 55, "wind": 16.8}
        ],
        "risk_assessment": {
            "composite_score": 65,
            "rain_score": 75,
            "temperature_score": 45,
            "wind_score": 55,
            "visibility_score": 40,
            "confidence": "Medium"
        }
    }
    
    # Sample historical data
    historical_data = {
        "month_percentile_rain": 78,
        "month_percentile_temp": 45,
        "monthly_averages": {
            "precipitation": 125.5,
            "temperature": 28.2
        }
    }
    
    return {
        "geocode": geocode_data,
        "weather": weather_data,
        "historical": historical_data
    }

def display_demo():
    """Display a demo of the ParadeGuard functionality."""
    
    print("🌧️ ParadeGuard - NASA 'Will it Rain on My Parade?' Dashboard")
    print("=" * 60)
    print()
    
    # Get sample data
    data = create_sample_data()
    
    # Location info
    print("📍 LOCATION ANALYSIS")
    print("-" * 30)
    print(f"Query: {data['geocode']['address']}")
    print(f"Resolved: {data['geocode']['formatted_address']}")
    print(f"Coordinates: {data['geocode']['latitude']:.4f}°, {data['geocode']['longitude']:.4f}°")
    print()
    
    # Current conditions
    current = data['weather']['current_conditions']
    print("🌤️ CURRENT CONDITIONS")
    print("-" * 30)
    print(f"Temperature: {current['temperature']:.1f}°C (feels like {current['feels_like']:.1f}°C)")
    print(f"Precipitation: {current['precipitation_mm']:.1f} mm ({current['precipitation_probability']}% chance)")
    print(f"Wind: {current['wind_speed']:.1f} km/h (gusts up to {current['wind_gusts']:.1f} km/h)")
    print(f"Humidity: {current['humidity']}%")
    print(f"Cloud Cover: {current['cloud_cover']}%")
    print(f"UV Index: {current['uv_index']}")
    print()
    
    # Risk assessment
    risk = data['weather']['risk_assessment']
    print("⚖️ RISK ASSESSMENT")
    print("-" * 30)
    print(f"Composite Risk Score: {risk['composite_score']}/100")
    print(f"  • Rain Risk: {risk['rain_score']}/100")
    print(f"  • Temperature Risk: {risk['temperature_score']}/100")
    print(f"  • Wind Risk: {risk['wind_score']}/100")
    print(f"  • Visibility Risk: {risk['visibility_score']}/100")
    print(f"Confidence: {risk['confidence']}")
    print()
    
    # Verdict
    if risk['composite_score'] >= 70:
        verdict = "🚨 HIGH RISK - Consider postponing outdoor activities"
    elif risk['composite_score'] >= 50:
        verdict = "⚠️ MODERATE RISK - Monitor conditions closely"
    else:
        verdict = "✅ LOW RISK - Good conditions for outdoor activities"
    
    print("🎯 VERDICT")
    print("-" * 30)
    print(verdict)
    print()
    
    # Hourly forecast
    print("📊 EVENING FORECAST (18:00-21:00)")
    print("-" * 30)
    for hour in data['weather']['hourly_forecast']:
        time_str = hour['time'].split('T')[1][:5]  # Extract time
        print(f"{time_str} | {hour['temp']:.1f}°C | {hour['precip']:.1f}mm | {hour['precip_prob']}% | {hour['wind']:.1f}km/h")
    print()
    
    # Historical context
    hist = data['historical']
    print("📈 HISTORICAL CONTEXT")
    print("-" * 30)
    print(f"Rain Percentile: {hist['month_percentile_rain']}% (wetter than {hist['month_percentile_rain']}% of May days)")
    print(f"Temperature Percentile: {hist['month_percentile_temp']}% (warmer than {hist['month_percentile_temp']}% of May days)")
    print(f"Monthly Average Rain: {hist['monthly_averages']['precipitation']:.1f}mm")
    print(f"Monthly Average Temp: {hist['monthly_averages']['temperature']:.1f}°C")
    print()
    
    # Recommendations
    print("💡 RECOMMENDATIONS")
    print("-" * 30)
    if risk['rain_score'] > 60:
        print("• Bring rain gear and have indoor backup plans")
    if risk['wind_score'] > 50:
        print("• Secure loose items and decorations")
    if current['uv_index'] > 6:
        print("• Use sun protection during daytime hours")
    if current['temperature'] > 30:
        print("• Stay hydrated and seek shade")
    print()
    
    print("📥 EXPORT OPTIONS")
    print("-" * 30)
    print("• CSV: Detailed weather data with metadata")
    print("• JSON: Complete analysis results")
    print("• Map: Interactive location visualization")
    print()
    
    print("🔗 DATA SOURCES")
    print("-" * 30)
    print("• Google Geocoding API - Location resolution")
    print("• Google Weather API - Current conditions")
    print("• Meteostat API - Historical climatology")
    print("• Open-Meteo API - Forecast data")
    print()
    
    print("=" * 60)
    print("This is a demonstration of ParadeGuard's capabilities.")
    print("To run the full application:")
    print("1. Install dependencies: pip3 install -r requirements.txt")
    print("2. Set up API keys in .env file")
    print("3. Run: streamlit run app/app.py")

def main():
    """Main demo function."""
    try:
        display_demo()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nDemo error: {e}")

if __name__ == "__main__":
    main()
