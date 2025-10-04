# ParadeGuard — NASA "Will it Rain on My Parade?" Dashboard

A Streamlit dashboard that provides weather risk analysis for events and parades. Users can query a location and date/time to get comprehensive weather forecasts, risk assessments, and historical context.

## Features

- **Location Resolution**: Google Geocoding API for precise location lookup
- **Current Conditions**: Google Weather API for real-time weather data
- **Forecast Data**: Open-Meteo API for hourly and daily forecasts
- **Historical Context**: Meteostat API for climatological baselines
- **Risk Assessment**: Composite scoring for rain, temperature, wind, and visibility
- **Interactive Visualizations**: Plotly charts and pydeck maps
- **Data Export**: CSV and JSON export with metadata

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Environment Variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

3. **Run the Application**
   ```bash
   streamlit run app/app.py
   ```

## API Keys Required

- **Google Maps API Key**: For geocoding locations
- **Google Weather API Key**: For current weather conditions
- **RapidAPI Key**: For Meteostat historical data

## Data Sources & Licenses

- **Google Geocoding**: [Google Maps Platform](https://developers.google.com/maps/documentation/geocoding)
- **Google Weather**: [Google Weather API](https://developers.google.com/maps/documentation/weather)
- **Meteostat**: [Meteostat API](https://meteostat.net/en/api) via RapidAPI
- **Open-Meteo**: [Open-Meteo](https://open-meteo.com/) - Free weather API
- **WMO Weather Codes**: Provided by Open-Meteo

## Usage

1. Enter a location (e.g., "Pathanamthitta, Kerala")
2. Select a date and time window
3. Click "Analyze" to get weather risk assessment
4. View detailed charts and historical context
5. Export data as CSV or JSON

## Risk Scoring

The composite risk score (0-100) considers:
- **Rain/Wetness (40%)**: Precipitation probability and intensity
- **Heat/Cold (25%)**: Apparent temperature comfort levels
- **Wind (20%)**: Wind speed and gust conditions
- **Sky/Visibility (15%)**: Cloud cover, visibility, and UV index

## Performance

- API responses are cached for 15 minutes
- Target response time: <2 seconds on Wi-Fi
- Graceful fallbacks for API failures

## Disclaimer

Weather forecasts are probabilistic and should be used as guidance only. Always check official weather services for critical decisions.