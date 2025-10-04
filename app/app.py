"""
ParadeGuard - NASA "Will it Rain on My Parade?" Dashboard
Main Streamlit application.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import logging
from typing import Optional

# Add the project root to Python path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
from app.core.schemas import UnifiedResult, QueryInputs
from app.core.config import validate_secrets
from app.core.risk import calculate_composite_risk_score, get_risk_band, get_risk_verdict
from app.core.timeutil import get_daypart_stats, format_time_window_display
from app.core.exporter import to_csv, to_json, get_export_filename
from app.core.maputil import create_paradeguard_map

from app.services.geocode import geocode_location, validate_geocode_result
from app.services.google_weather import get_current_weather, validate_weather_result
from app.services.meteostat import get_monthly_climatology, validate_meteostat_result
from app.services.open_meteo import get_forecast_data, validate_forecast_data, get_timezone_from_forecast

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="ParadeGuard - Weather Risk Dashboard",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .risk-score {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .risk-low { background-color: #d4edda; color: #155724; }
    .risk-moderate { background-color: #fff3cd; color: #856404; }
    .risk-high { background-color: #f8d7da; color: #721c24; }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .footer {
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 1px solid #dee2e6;
        font-size: 0.8rem;
        color: #6c757d;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function."""
    
    # Header
    st.markdown('<h1 class="main-header">🌧️ ParadeGuard</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">NASA "Will it Rain on My Parade?" Weather Risk Dashboard</p>', unsafe_allow_html=True)
    
    # Check API keys
    secrets_valid, missing_keys = validate_secrets()
    if not secrets_valid:
        st.error(f"Missing API keys: {', '.join(missing_keys)}. Please check your configuration.")
        st.stop()
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("📍 Location & Time")
        
        # Location input
        place = st.text_input(
            "Location",
            value="Pathanamthitta, Kerala",
            help="Enter a city, address, or landmark"
        )
        
        # Date input
        selected_date = st.date_input(
            "Date",
            value=date.today() + timedelta(days=1),
            min_value=date.today(),
            max_value=date.today() + timedelta(days=7)
        )
        
        # Time window selection
        time_window = st.selectbox(
            "Time Window",
            options=["Morning", "Afternoon", "Evening", "Night"],
            index=2,  # Default to Evening
            help="Select the time period for your event"
        )
        
        st.markdown(f"**Selected Window:** {format_time_window_display(time_window)}")
        
        # Analyze button
        analyze_clicked = st.button("🔍 Analyze Weather Risk", type="primary", use_container_width=True)
    
    # Main content area
    if analyze_clicked and place:
        with st.spinner("Analyzing weather conditions..."):
            result = analyze_weather_risk(place, selected_date, time_window)
            
            if result:
                display_results(result)
            else:
                st.error("Unable to analyze weather conditions. Please try again.")
    else:
        # Show welcome message
        st.markdown("""
        ### Welcome to ParadeGuard! 🎉
        
        This dashboard helps you assess weather risks for your events and parades. 
        
        **How to use:**
        1. Enter your location in the sidebar
        2. Select the date and time window for your event
        3. Click "Analyze Weather Risk" to get a comprehensive assessment
        
        **What you'll get:**
        - Risk score and plain-language verdict
        - Detailed weather charts and forecasts
        - Historical context and climatology
        - Interactive map of your location
        - Exportable data in CSV/JSON formats
        
        Get started by entering a location in the sidebar! 🌤️
        """)


def analyze_weather_risk(place: str, selected_date: date, time_window: str) -> Optional[UnifiedResult]:
    """Analyze weather risk for the given inputs."""
    
    try:
        # Create query inputs
        query_inputs = QueryInputs(
            place=place,
            date=datetime.combine(selected_date, datetime.min.time()),
            time_window=time_window
        )
        
        # Step 1: Geocode location
        st.info("📍 Resolving location...")
        geocode_result = geocode_location(place)
        is_valid, error_msg = validate_geocode_result(geocode_result)
        
        if not is_valid:
            st.error(error_msg)
            return None
        
        # Step 2: Get timezone
        timezone = get_timezone_from_forecast(geocode_result.lat, geocode_result.lon)
        
        # Step 3: Fetch weather data (parallel where possible)
        st.info("🌤️ Fetching weather data...")
        
        # Current conditions
        current_google = get_current_weather(geocode_result.lat, geocode_result.lon)
        current_openmeteo, hourly, daily = get_forecast_data(geocode_result.lat, geocode_result.lon)
        
        # Historical data
        st.info("📊 Fetching historical context...")
        historical = get_monthly_climatology(geocode_result.lat, geocode_result.lon)
        
        # Step 4: Calculate risk score
        st.info("⚖️ Calculating risk assessment...")
        risk_score = calculate_composite_risk_score(hourly, current_openmeteo, current_google)
        
        # Step 5: Create unified result
        result = UnifiedResult(
            inputs=query_inputs,
            geocode=geocode_result,
            current_google=current_google,
            current_openmeteo=current_openmeteo,
            hourly=hourly,
            daily=daily,
            historical=historical,
            risk_score=risk_score,
            timezone=timezone,
            notes=[],
            metadata={
                "analysis_timestamp": datetime.now().isoformat(),
                "data_sources": ["Google Geocoding", "Google Weather", "Meteostat", "Open-Meteo"]
            }
        )
        
        # Add notes for any missing data
        if not current_google:
            result.notes.append("Google Weather data unavailable; using Open-Meteo current conditions")
        if not historical:
            result.notes.append("Historical climatology data unavailable for this location")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in weather analysis: {e}")
        st.error(f"An error occurred during analysis: {str(e)}")
        return None


def display_results(result: UnifiedResult):
    """Display the analysis results."""
    
    # Above-the-fold summary
    display_summary(result)
    
    # Tabs for detailed views
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🌧️ Rain", "🌡️ Heat/Comfort", "💨 Wind", "☁️ Sky/UV", "📊 Historical", "🗺️ Map"
    ])
    
    with tab1:
        display_rain_tab(result)
    
    with tab2:
        display_heat_comfort_tab(result)
    
    with tab3:
        display_wind_tab(result)
    
    with tab4:
        display_sky_uv_tab(result)
    
    with tab5:
        display_historical_tab(result)
    
    with tab6:
        display_map_tab(result)
    
    # Export section
    display_export_section(result)
    
    # Footer
    display_footer()


def display_summary(result: UnifiedResult):
    """Display the above-the-fold summary."""
    
    st.markdown("---")
    
    # Location info
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"**📍 {result.geocode.formatted_address}**")
        st.markdown(f"**📅 {result.inputs.date.strftime('%A, %B %d, %Y')}**")
        st.markdown(f"**🕐 {result.inputs.time_window} ({format_time_window_display(result.inputs.time_window)})**")
    
    with col2:
        st.markdown(f"**🌍 {result.geocode.lat:.4f}°, {result.geocode.lon:.4f}°**")
        st.markdown(f"**🕐 {result.timezone}**")
    
    with col3:
        if result.current_openmeteo and result.current_openmeteo.temperature_2m:
            st.metric("Current Temp", f"{result.current_openmeteo.temperature_2m:.1f}°C")
        if result.current_openmeteo and result.current_openmeteo.precipitation:
            st.metric("Current Rain", f"{result.current_openmeteo.precipitation:.1f} mm")
    
    # Risk assessment
    if result.risk_score:
        risk_band, risk_color = get_risk_band(result.risk_score.composite_score)
        verdict = get_risk_verdict(result.risk_score.composite_score, result.inputs.time_window)
        
        st.markdown(f"### {verdict}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f'<div class="risk-score risk-{risk_color}">{result.risk_score.composite_score:.0f}/100</div>', unsafe_allow_html=True)
            st.markdown(f"**Risk Level: {risk_band}**")
        
        with col2:
            st.metric("Rain Risk", f"{result.risk_score.rain_score:.0f}/100")
        
        with col3:
            st.metric("Temperature Risk", f"{result.risk_score.temperature_score:.0f}/100")
        
        with col4:
            st.metric("Wind Risk", f"{result.risk_score.wind_score:.0f}/100")
        
        # Confidence
        confidence_color = "green" if result.risk_score.confidence == "High" else "orange" if result.risk_score.confidence == "Medium" else "red"
        st.markdown(f"**Confidence: <span style='color: {confidence_color}'>{result.risk_score.confidence}</span>**", unsafe_allow_html=True)
    
    st.markdown("---")


def display_rain_tab(result: UnifiedResult):
    """Display rain forecast tab."""
    
    if not result.hourly:
        st.warning("Hourly forecast data not available.")
        return
    
    # Get daypart stats
    daypart_stats = get_daypart_stats(
        result.hourly.time,
        result.hourly.precipitation,
        result.inputs.date,
        result.inputs.time_window,
        result.timezone
    )
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if daypart_stats["sum"] is not None:
            st.metric("Expected Rain", f"{daypart_stats['sum']:.1f} mm")
        else:
            st.metric("Expected Rain", "N/A")
    
    with col2:
        if result.hourly.precipitation_probability:
            prob_stats = get_daypart_stats(
                result.hourly.time,
                result.hourly.precipitation_probability,
                result.inputs.date,
                result.inputs.time_window,
                result.timezone
            )
            if prob_stats["max"] is not None:
                st.metric("Max Rain Probability", f"{prob_stats['max']:.0f}%")
            else:
                st.metric("Max Rain Probability", "N/A")
    
    with col3:
        if daypart_stats["max"] is not None:
            st.metric("Peak Intensity", f"{daypart_stats['max']:.1f} mm/h")
        else:
            st.metric("Peak Intensity", "N/A")
    
    with col4:
        if result.daily and result.daily.precipitation_sum:
            daily_precip = result.daily.precipitation_sum[0] if result.daily.precipitation_sum[0] is not None else 0
            st.metric("Daily Total", f"{daily_precip:.1f} mm")
        else:
            st.metric("Daily Total", "N/A")
    
    # Hourly chart
    if result.hourly.time and result.hourly.precipitation:
        # Create hourly chart
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add precipitation bars
        fig.add_trace(
            go.Bar(
                x=result.hourly.time,
                y=result.hourly.precipitation,
                name="Precipitation (mm/h)",
                marker_color="lightblue",
                opacity=0.7
            ),
            secondary_y=False
        )
        
        # Add probability line
        if result.hourly.precipitation_probability:
            fig.add_trace(
                go.Scatter(
                    x=result.hourly.time,
                    y=result.hourly.precipitation_probability,
                    name="Rain Probability (%)",
                    line=dict(color="red", width=2),
                    mode="lines+markers"
                ),
                secondary_y=True
            )
        
        # Update layout
        fig.update_layout(
            title="Hourly Precipitation Forecast",
            xaxis_title="Time",
            height=400
        )
        
        fig.update_yaxes(title_text="Precipitation (mm/h)", secondary_y=False)
        fig.update_yaxes(title_text="Probability (%)", secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Daily summary
    if result.daily and result.daily.time:
        st.subheader("Daily Summary")
        
        daily_data = []
        for i in range(min(7, len(result.daily.time))):
            daily_data.append({
                "Date": result.daily.time[i].strftime("%Y-%m-%d"),
                "Precipitation (mm)": result.daily.precipitation_sum[i] if i < len(result.daily.precipitation_sum) else None,
                "Rain (mm)": result.daily.rain_sum[i] if i < len(result.daily.rain_sum) else None,
                "Rainy Hours": result.daily.precipitation_hours[i] if i < len(result.daily.precipitation_hours) else None,
                "Max Prob (%)": result.daily.precipitation_probability_max[i] if i < len(result.daily.precipitation_probability_max) else None
            })
        
        df = pd.DataFrame(daily_data)
        st.dataframe(df, use_container_width=True)


def display_heat_comfort_tab(result: UnifiedResult):
    """Display heat/comfort tab."""
    
    if not result.hourly:
        st.warning("Hourly forecast data not available.")
        return
    
    # Get daypart stats
    temp_stats = get_daypart_stats(
        result.hourly.time,
        result.hourly.temperature_2m,
        result.inputs.date,
        result.inputs.time_window,
        result.timezone
    )
    
    app_temp_stats = get_daypart_stats(
        result.hourly.time,
        result.hourly.apparent_temperature,
        result.inputs.date,
        result.inputs.time_window,
        result.timezone
    )
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if temp_stats["mean"] is not None:
            st.metric("Avg Temperature", f"{temp_stats['mean']:.1f}°C")
        else:
            st.metric("Avg Temperature", "N/A")
    
    with col2:
        if app_temp_stats["mean"] is not None:
            st.metric("Avg Feels Like", f"{app_temp_stats['mean']:.1f}°C")
        else:
            st.metric("Avg Feels Like", "N/A")
    
    with col3:
        if temp_stats["max"] is not None and temp_stats["min"] is not None:
            st.metric("Temperature Range", f"{temp_stats['min']:.1f}°C - {temp_stats['max']:.1f}°C")
        else:
            st.metric("Temperature Range", "N/A")
    
    with col4:
        if result.hourly.relative_humidity_2m:
            humidity_stats = get_daypart_stats(
                result.hourly.time,
                result.hourly.relative_humidity_2m,
                result.inputs.date,
                result.inputs.time_window,
                result.timezone
            )
            if humidity_stats["mean"] is not None:
                st.metric("Avg Humidity", f"{humidity_stats['mean']:.0f}%")
            else:
                st.metric("Avg Humidity", "N/A")
    
    # Temperature chart
    if result.hourly.time and result.hourly.temperature_2m:
        fig = go.Figure()
        
        # Add temperature line
        fig.add_trace(go.Scatter(
            x=result.hourly.time,
            y=result.hourly.temperature_2m,
            name="Temperature",
            line=dict(color="blue", width=2),
            mode="lines+markers"
        ))
        
        # Add apparent temperature line
        if result.hourly.apparent_temperature:
            fig.add_trace(go.Scatter(
                x=result.hourly.time,
                y=result.hourly.apparent_temperature,
                name="Feels Like",
                line=dict(color="red", width=2),
                mode="lines+markers"
            ))
        
        # Add comfort zones
        fig.add_hline(y=18, line_dash="dash", line_color="lightblue", annotation_text="Cool threshold")
        fig.add_hline(y=32, line_dash="dash", line_color="orange", annotation_text="Hot threshold")
        
        fig.update_layout(
            title="Temperature Forecast",
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Comfort assessment
    if app_temp_stats["min"] is not None and app_temp_stats["max"] is not None:
        st.subheader("Comfort Assessment")
        
        if app_temp_stats["min"] < 18:
            st.warning("⚠️ Cool conditions expected - consider warm clothing")
        elif app_temp_stats["max"] > 32:
            st.warning("⚠️ Hot conditions expected - stay hydrated and seek shade")
        else:
            st.success("✅ Comfortable temperature range expected")


def display_wind_tab(result: UnifiedResult):
    """Display wind forecast tab."""
    
    if not result.hourly:
        st.warning("Hourly forecast data not available.")
        return
    
    # Get daypart stats
    wind_stats = get_daypart_stats(
        result.hourly.time,
        result.hourly.wind_speed_10m,
        result.inputs.date,
        result.inputs.time_window,
        result.timezone
    )
    
    gust_stats = get_daypart_stats(
        result.hourly.time,
        result.hourly.wind_gusts_10m,
        result.inputs.date,
        result.inputs.time_window,
        result.timezone
    )
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if wind_stats["mean"] is not None:
            st.metric("Avg Wind Speed", f"{wind_stats['mean']:.1f} km/h")
        else:
            st.metric("Avg Wind Speed", "N/A")
    
    with col2:
        if gust_stats["max"] is not None:
            st.metric("Max Wind Gusts", f"{gust_stats['max']:.1f} km/h")
        else:
            st.metric("Max Wind Gusts", "N/A")
    
    with col3:
        if wind_stats["max"] is not None:
            st.metric("Peak Wind Speed", f"{wind_stats['max']:.1f} km/h")
        else:
            st.metric("Peak Wind Speed", "N/A")
    
    with col4:
        if result.daily and result.daily.wind_speed_10m_max:
            daily_max_wind = result.daily.wind_speed_10m_max[0] if result.daily.wind_speed_10m_max[0] is not None else 0
            st.metric("Daily Max Wind", f"{daily_max_wind:.1f} km/h")
        else:
            st.metric("Daily Max Wind", "N/A")
    
    # Wind chart
    if result.hourly.time and result.hourly.wind_speed_10m:
        fig = go.Figure()
        
        # Add wind speed line
        fig.add_trace(go.Scatter(
            x=result.hourly.time,
            y=result.hourly.wind_speed_10m,
            name="Wind Speed",
            line=dict(color="green", width=2),
            mode="lines+markers"
        ))
        
        # Add wind gusts line
        if result.hourly.wind_gusts_10m:
            fig.add_trace(go.Scatter(
                x=result.hourly.time,
                y=result.hourly.wind_gusts_10m,
                name="Wind Gusts",
                line=dict(color="red", width=2),
                mode="lines+markers"
            ))
        
        # Add wind thresholds
        fig.add_hline(y=35, line_dash="dash", line_color="orange", annotation_text="Caution threshold")
        fig.add_hline(y=55, line_dash="dash", line_color="red", annotation_text="High risk threshold")
        
        fig.update_layout(
            title="Wind Speed Forecast",
            xaxis_title="Time",
            yaxis_title="Wind Speed (km/h)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Wind direction (simplified)
    if result.hourly.wind_direction_10m:
        st.subheader("Wind Direction")
        
        # Get wind directions for the time window
        filtered_times, filtered_directions = get_daypart_stats(
            result.hourly.time,
            result.hourly.wind_direction_10m,
            result.inputs.date,
            result.inputs.time_window,
            result.timezone
        )
        
        if filtered_directions and any(d is not None for d in filtered_directions):
            # Simple wind direction display
            valid_directions = [d for d in filtered_directions if d is not None]
            if valid_directions:
                avg_direction = sum(valid_directions) / len(valid_directions)
                
                # Convert to compass direction
                directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
                direction_index = int((avg_direction + 11.25) / 22.5) % 16
                compass_direction = directions[direction_index]
                
                st.metric("Primary Wind Direction", f"{compass_direction} ({avg_direction:.0f}°)")
    
    # Wind assessment
    if gust_stats["max"] is not None:
        st.subheader("Wind Assessment")
        
        if gust_stats["max"] >= 55:
            st.error("🚨 High wind risk - consider postponing outdoor activities")
        elif gust_stats["max"] >= 35:
            st.warning("⚠️ Moderate wind risk - secure loose items")
        else:
            st.success("✅ Low wind risk")


def display_sky_uv_tab(result: UnifiedResult):
    """Display sky/UV forecast tab."""
    
    if not result.hourly:
        st.warning("Hourly forecast data not available.")
        return
    
    # Get daypart stats
    cloud_stats = get_daypart_stats(
        result.hourly.time,
        result.hourly.cloud_cover,
        result.inputs.date,
        result.inputs.time_window,
        result.timezone
    )
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if cloud_stats["mean"] is not None:
            st.metric("Avg Cloud Cover", f"{cloud_stats['mean']:.0f}%")
        else:
            st.metric("Avg Cloud Cover", "N/A")
    
    with col2:
        if result.daily and result.daily.uv_index_max:
            daily_uv = result.daily.uv_index_max[0] if result.daily.uv_index_max[0] is not None else 0
            st.metric("Max UV Index", f"{daily_uv:.0f}")
        else:
            st.metric("Max UV Index", "N/A")
    
    with col3:
        if result.daily and result.daily.sunrise:
            sunrise = result.daily.sunrise[0] if result.daily.sunrise[0] else None
            if sunrise:
                st.metric("Sunrise", sunrise.strftime("%H:%M"))
            else:
                st.metric("Sunrise", "N/A")
        else:
            st.metric("Sunrise", "N/A")
    
    with col4:
        if result.daily and result.daily.sunset:
            sunset = result.daily.sunset[0] if result.daily.sunset[0] else None
            if sunset:
                st.metric("Sunset", sunset.strftime("%H:%M"))
            else:
                st.metric("Sunset", "N/A")
        else:
            st.metric("Sunset", "N/A")
    
    # Cloud cover chart
    if result.hourly.time and result.hourly.cloud_cover:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=result.hourly.time,
            y=result.hourly.cloud_cover,
            name="Cloud Cover",
            line=dict(color="gray", width=2),
            mode="lines+markers",
            fill="tonexty"
        ))
        
        # Add cloud thresholds
        fig.add_hline(y=80, line_dash="dash", line_color="darkgray", annotation_text="Heavy cloud")
        
        fig.update_layout(
            title="Cloud Cover Forecast",
            xaxis_title="Time",
            yaxis_title="Cloud Cover (%)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Daylight duration
    if result.daily and result.daily.daylight_duration:
        st.subheader("Daylight Information")
        
        daylight_hours = result.daily.daylight_duration[0] if result.daily.daylight_duration[0] is not None else 0
        st.metric("Daylight Duration", f"{daylight_hours:.1f} hours")
    
    # UV assessment
    if result.daily and result.daily.uv_index_max:
        st.subheader("UV Assessment")
        
        max_uv = result.daily.uv_index_max[0] if result.daily.uv_index_max[0] is not None else 0
        
        if max_uv >= 7:
            st.warning("⚠️ High UV exposure - use sun protection")
        elif max_uv >= 3:
            st.info("ℹ️ Moderate UV exposure - some protection recommended")
        else:
            st.success("✅ Low UV exposure")


def display_historical_tab(result: UnifiedResult):
    """Display historical context tab."""
    
    if not result.historical:
        st.warning("Historical climatology data not available for this location.")
        return
    
    st.subheader("Historical Context")
    
    # Month percentiles
    col1, col2 = st.columns(2)
    
    with col1:
        if result.historical.month_percentile_rain is not None:
            st.metric(
                "Rain Percentile", 
                f"{result.historical.month_percentile_rain:.0f}%",
                help="How this month's rainfall compares to historical average"
            )
        else:
            st.metric("Rain Percentile", "N/A")
    
    with col2:
        if result.historical.month_percentile_temp is not None:
            st.metric(
                "Temperature Percentile", 
                f"{result.historical.month_percentile_temp:.0f}%",
                help="How this month's temperature compares to historical average"
            )
        else:
            st.metric("Temperature Percentile", "N/A")
    
    # Historical data table
    if result.historical.data:
        st.subheader("Monthly Climatology (Last 10 Years)")
        
        historical_data = []
        for row in result.historical.data:
            historical_data.append({
                "Date": row.date,
                "Avg Temp (°C)": row.tavg,
                "Min Temp (°C)": row.tmin,
                "Max Temp (°C)": row.tmax,
                "Precipitation (mm)": row.prcp,
                "Sunshine (hrs)": row.tsun,
                "Pressure (hPa)": row.pres
            })
        
        df = pd.DataFrame(historical_data)
        st.dataframe(df, use_container_width=True)


def display_map_tab(result: UnifiedResult):
    """Display map tab."""
    
    if not result.geocode:
        st.warning("Location data not available.")
        return
    
    st.subheader("Location Map")
    
    # Create map
    deck = create_paradeguard_map(
        lat=result.geocode.lat,
        lon=result.geocode.lon,
        address=result.geocode.formatted_address,
        date=result.inputs.date.strftime("%Y-%m-%d"),
        time_window=result.inputs.time_window
    )
    
    st.pydeck_chart(deck, use_container_width=True)


def display_export_section(result: UnifiedResult):
    """Display export section."""
    
    st.markdown("---")
    st.subheader("📥 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV export
        csv_data = to_csv(result)
        csv_filename = get_export_filename(result, "csv")
        
        st.download_button(
            label="📊 Download CSV",
            data=csv_data,
            file_name=csv_filename,
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # JSON export
        json_data = to_json(result)
        json_filename = get_export_filename(result, "json")
        
        st.download_button(
            label="📋 Download JSON",
            data=json_data,
            file_name=json_filename,
            mime="application/json",
            use_container_width=True
        )


def display_footer():
    """Display footer with attribution and compliance information."""
    
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <p><strong>Data Sources:</strong> Google Geocoding API, Google Weather API, Meteostat API (via RapidAPI), Open-Meteo API</p>
        <p><strong>Attribution:</strong> WMO weather codes provided by Open-Meteo. See README.md for full license information.</p>
        <p><strong>Disclaimer:</strong> Weather forecasts are probabilistic and should be used as guidance only. Always check official weather services for critical decisions.</p>
        <p><strong>ParadeGuard v1.0</strong> - NASA Space Apps "Will it Rain on My Parade?" Challenge</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
