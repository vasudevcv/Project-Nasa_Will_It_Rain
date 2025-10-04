# ParadeGuard Setup Instructions

## Prerequisites

1. **Python 3.10+** (you have Python 3.12.3 ✅)
2. **pip** (Python package installer)

## Installation Steps

### 1. Install pip (if not already installed)

On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3-pip
```

On other systems, follow the [pip installation guide](https://pip.pypa.io/en/stable/installation/).

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Set Up Environment Variables

Copy the example environment file and add your API keys:

```bash
cp env.example .env
```

Edit `.env` and add your API keys:
```
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
GOOGLE_WEATHER_API_KEY=your_google_weather_api_key_here
RAPIDAPI_KEY=your_rapidapi_key_here
```

### 4. Test Installation

```bash
python3 test_installation.py
```

### 5. Run the Application

```bash
streamlit run app/app.py
```

## API Keys Required

You'll need API keys for:

1. **Google Maps API** - For geocoding locations
   - Get it from [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Geocoding API

2. **Google Weather API** - For current weather conditions
   - Get it from [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Weather API

3. **RapidAPI Key** - For Meteostat historical data
   - Get it from [RapidAPI](https://rapidapi.com/)
   - Subscribe to the Meteostat API

## Alternative: Using uv (Faster Package Manager)

If you have `uv` installed:

```bash
uv pip install -r requirements.txt
```

## Troubleshooting

### Import Errors
If you get import errors, make sure all dependencies are installed:
```bash
pip3 install --upgrade -r requirements.txt
```

### API Key Errors
Make sure your `.env` file is in the project root and contains valid API keys.

### Port Issues
If Streamlit can't start, try specifying a different port:
```bash
streamlit run app/app.py --server.port 8502
```

## Quick Start (After Installation)

1. Open your browser to `http://localhost:8501`
2. Enter a location (e.g., "Pathanamthitta, Kerala")
3. Select a date and time window
4. Click "Analyze Weather Risk"
5. View the comprehensive weather analysis!

## Features

- 🌍 **Location Resolution**: Google Geocoding API
- 🌤️ **Current Conditions**: Google Weather API  
- 📊 **Forecast Data**: Open-Meteo API
- 📈 **Historical Context**: Meteostat API
- ⚖️ **Risk Assessment**: Composite scoring algorithm
- 📱 **Interactive UI**: Streamlit dashboard
- 🗺️ **Maps**: pydeck visualization
- 📥 **Export**: CSV/JSON data export

## Support

For issues or questions, check the README.md file or create an issue in the project repository.
