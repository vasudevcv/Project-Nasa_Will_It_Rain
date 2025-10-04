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
        analyze_clicked = st.button("🔍 Analyze Weather Risk", type="primary", width='stretch')
    
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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🌧️ Rain", "🌡️ Heat/Comfort", "💨 Wind", "☁️ Sky/UV", "📊 Pressure", "🔬 Advanced", "📈 Historical", "🗺️ Map"
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
        display_pressure_tab(result)
    
    with tab6:
        display_advanced_tab(result)
    
    with tab7:
        display_historical_tab(result)
    
    with tab8:
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
        if result.current_openmeteo and result.current_openmeteo.apparent_temperature:
            st.metric("Feels Like", f"{result.current_openmeteo.apparent_temperature:.1f}°C")
        if result.current_openmeteo and result.current_openmeteo.precipitation:
            st.metric("Current Rain", f"{result.current_openmeteo.precipitation:.1f} mm")
        if result.current_openmeteo and result.current_openmeteo.wind_speed_10m:
            st.metric("Wind Speed", f"{result.current_openmeteo.wind_speed_10m:.1f} km/h")
        if result.current_openmeteo and result.current_openmeteo.relative_humidity_2m:
            st.metric("Humidity", f"{result.current_openmeteo.relative_humidity_2m:.0f}%")
        if result.current_openmeteo and result.current_openmeteo.surface_pressure:
            st.metric("Pressure", f"{result.current_openmeteo.surface_pressure:.0f} hPa")
        else:
            st.metric("Pressure", "N/A")
    
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
        
        # Debug info (remove in production)
        with st.expander("🔍 Debug Info"):
            st.write("**Risk Score Details:**")
            st.write(f"- Composite: {result.risk_score.composite_score}")
            st.write(f"- Rain: {result.risk_score.rain_score}")
            st.write(f"- Temperature: {result.risk_score.temperature_score}")
            st.write(f"- Wind: {result.risk_score.wind_score}")
            st.write(f"- Visibility: {result.risk_score.visibility_score}")
            st.write(f"- Confidence: {result.risk_score.confidence} ({result.risk_score.confidence_value})")
            
            if result.hourly:
                st.write(f"**Hourly Data Available:** {len(result.hourly.time)} hours")
                if result.hourly.precipitation:
                    st.write(f"**Precipitation Data:** {len([x for x in result.hourly.precipitation if x is not None])} valid values")
            else:
                st.write("**Hourly Data:** Not available")
    else:
        st.warning("Risk assessment not available.")
    
    # Add hourly forecast graph
    if result.hourly and result.hourly.time and result.hourly.temperature_2m:
        st.subheader("📊 Hourly Forecast")
        
        # Get data for the selected date
        target_date = result.inputs.date
        hourly_times = []
        hourly_temps = []
        hourly_precip = []
        hourly_precip_prob = []
        
        for i, dt in enumerate(result.hourly.time):
            if dt and dt.date() == target_date:
                hourly_times.append(dt.strftime("%H:%M"))
                if i < len(result.hourly.temperature_2m) and result.hourly.temperature_2m[i] is not None:
                    hourly_temps.append(result.hourly.temperature_2m[i])
                else:
                    hourly_temps.append(None)
                
                if i < len(result.hourly.precipitation) and result.hourly.precipitation[i] is not None:
                    hourly_precip.append(result.hourly.precipitation[i])
                else:
                    hourly_precip.append(0)
                
                if i < len(result.hourly.precipitation_probability) and result.hourly.precipitation_probability[i] is not None:
                    hourly_precip_prob.append(result.hourly.precipitation_probability[i])
                else:
                    hourly_precip_prob.append(0)
        
        if hourly_times:
            # Create dual-axis chart
            fig = go.Figure()
            
            # Add temperature line
            fig.add_trace(go.Scatter(
                x=hourly_times,
                y=hourly_temps,
                mode='lines+markers',
                name='Temperature (°C)',
                line=dict(color='red', width=3),
                marker=dict(size=6),
                yaxis='y'
            ))
            
            # Add precipitation probability bars
            fig.add_trace(go.Bar(
                x=hourly_times,
                y=hourly_precip_prob,
                name='Rain Probability (%)',
                marker_color='lightblue',
                opacity=0.7,
                yaxis='y2'
            ))
            
            # Update layout
            fig.update_layout(
                title=f"Hourly Forecast for {target_date.strftime('%A, %B %d, %Y')}",
                xaxis_title="Time",
                yaxis=dict(
                    title="Temperature (°C)",
                    side="left",
                    color="red"
                ),
                yaxis2=dict(
                    title="Rain Probability (%)",
                    side="right",
                    overlaying="y",
                    range=[0, 100],
                    color="blue"
                ),
                hovermode='x unified',
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig, width='stretch')
    
    # Add weather insights section
    st.subheader("🌤️ Weather Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📊 Current Conditions**")
        if result.current_openmeteo:
            if result.current_openmeteo.weather_code:
                # Weather code interpretation
                weather_descriptions = {
                    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                    45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
                    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
                    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
                    85: "Slight snow showers", 86: "Heavy snow showers", 95: "Thunderstorm",
                    96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
                }
                weather_desc = weather_descriptions.get(result.current_openmeteo.weather_code, "Unknown")
                st.write(f"**Condition:** {weather_desc}")
            
            if result.current_openmeteo.is_day is not None:
                time_of_day = "Day" if result.current_openmeteo.is_day else "Night"
                st.write(f"**Time:** {time_of_day}")
    
    with col2:
        st.markdown("**🌡️ Comfort Index**")
        if result.current_openmeteo and result.current_openmeteo.apparent_temperature and result.current_openmeteo.relative_humidity_2m:
            temp = result.current_openmeteo.apparent_temperature
            humidity = result.current_openmeteo.relative_humidity_2m
            
            # Simple comfort calculation
            if temp < 18:
                comfort = "Cool"
                comfort_color = "blue"
            elif temp > 32:
                comfort = "Hot"
                comfort_color = "red"
            elif humidity > 80:
                comfort = "Humid"
                comfort_color = "orange"
            elif humidity < 30:
                comfort = "Dry"
                comfort_color = "yellow"
            else:
                comfort = "Comfortable"
                comfort_color = "green"
            
            st.write(f"**Comfort Level:** {comfort}")
            
            # Heat index approximation
            if temp > 26 and humidity > 40:
                heat_index = temp + 0.5 * humidity - 10
                st.write(f"**Heat Index:** {heat_index:.1f}°C")
    
    with col3:
        st.markdown("**🌬️ Wind Analysis**")
        if result.current_openmeteo and result.current_openmeteo.wind_speed_10m:
            wind_speed = result.current_openmeteo.wind_speed_10m
            
            if wind_speed < 5:
                wind_desc = "Calm"
            elif wind_speed < 15:
                wind_desc = "Light breeze"
            elif wind_speed < 25:
                wind_desc = "Moderate breeze"
            elif wind_speed < 35:
                wind_desc = "Fresh breeze"
            else:
                wind_desc = "Strong wind"
            
            st.write(f"**Wind:** {wind_desc}")
            
            if result.current_openmeteo.wind_direction_10m:
                direction = result.current_openmeteo.wind_direction_10m
                directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
                direction_index = int((direction + 11.25) / 22.5) % 16
                compass_direction = directions[direction_index]
                st.write(f"**Direction:** {compass_direction}")
    
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
        
        st.plotly_chart(fig, width='stretch')
    
    # Rain insights section
    st.subheader("🌧️ Rain Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📈 Rain Trends**")
        if result.hourly and result.hourly.precipitation:
            # Calculate rain trends
            valid_precip = [p for p in result.hourly.precipitation if p is not None and p > 0]
            if valid_precip:
                total_rain = sum(valid_precip)
                max_rain = max(valid_precip)
                avg_rain = total_rain / len(valid_precip)
                
                st.write(f"**Total Expected:** {total_rain:.1f} mm")
                st.write(f"**Peak Intensity:** {max_rain:.1f} mm/h")
                st.write(f"**Average:** {avg_rain:.1f} mm/h")
            else:
                st.write("**No significant rain expected**")
    
    with col2:
        st.markdown("**⏰ Best Times**")
        if result.hourly and result.hourly.precipitation_probability:
            # Find best times (lowest rain probability)
            prob_data = []
            for i, prob in enumerate(result.hourly.precipitation_probability):
                if prob is not None and i < len(result.hourly.time):
                    prob_data.append((result.hourly.time[i], prob))
            
            if prob_data:
                # Sort by probability (ascending)
                prob_data.sort(key=lambda x: x[1])
                best_times = prob_data[:3]  # Top 3 best times
                
                st.write("**Lowest rain risk:**")
                for time, prob in best_times:
                    if time:
                        st.write(f"• {time.strftime('%H:%M')} ({prob:.0f}%)")
    
    with col3:
        st.markdown("**⚠️ Rain Alerts**")
        if result.hourly and result.hourly.precipitation_probability:
            # Find high probability times
            high_prob_times = []
            for i, prob in enumerate(result.hourly.precipitation_probability):
                if prob is not None and prob > 70 and i < len(result.hourly.time):
                    high_prob_times.append((result.hourly.time[i], prob))
            
            if high_prob_times:
                st.write("**High rain risk:**")
                for time, prob in high_prob_times[:3]:  # Show top 3
                    if time:
                        st.write(f"• {time.strftime('%H:%M')} ({prob:.0f}%)")
            else:
                st.write("**No high-risk periods**")
    
    # Daily summary
    if result.daily and result.daily.time:
        st.subheader("Daily Summary")
        
        daily_data = []
        for i in range(min(7, len(result.daily.time))):
            daily_data.append({
                "Date": result.daily.time[i].strftime("%a, %b %d"),
                "Max Temp (°C)": result.daily.temperature_2m_max[i] if i < len(result.daily.temperature_2m_max) else None,
                "Min Temp (°C)": result.daily.temperature_2m_min[i] if i < len(result.daily.temperature_2m_min) else None,
                "Feels Like Max (°C)": result.daily.apparent_temperature_max[i] if i < len(result.daily.apparent_temperature_max) else None,
                "Precipitation (mm)": result.daily.precipitation_sum[i] if i < len(result.daily.precipitation_sum) else None,
                "Rain (mm)": result.daily.rain_sum[i] if i < len(result.daily.rain_sum) else None,
                "Showers (mm)": "N/A",  # Not available in simplified version
                "Rainy Hours": result.daily.precipitation_hours[i] if i < len(result.daily.precipitation_hours) else None,
                "Max Prob (%)": result.daily.precipitation_probability_max[i] if i < len(result.daily.precipitation_probability_max) else None,
                "Wind Max (km/h)": result.daily.wind_speed_10m_max[i] if i < len(result.daily.wind_speed_10m_max) else None,
                "UV Index": result.daily.uv_index_max[i] if i < len(result.daily.uv_index_max) else None,
                "Pressure Max (hPa)": "N/A",  # Not available in simplified version
                "Pressure Min (hPa)": "N/A"  # Not available in simplified version
            })
        
        df = pd.DataFrame(daily_data)
        st.dataframe(df, width='stretch')


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
        
        st.plotly_chart(fig, width='stretch')
    
    # Humidity and comfort chart
    if result.hourly.relative_humidity_2m and result.hourly.dew_point_2m:
        st.subheader("Humidity & Comfort Analysis")
        
        # Get data for the selected date
        target_date = result.inputs.date
        comfort_times = []
        humidity_data = []
        dew_point_data = []
        
        for i, dt in enumerate(result.hourly.time):
            if dt and dt.date() == target_date:
                comfort_times.append(dt.strftime("%H:%M"))
                
                if i < len(result.hourly.relative_humidity_2m) and result.hourly.relative_humidity_2m[i] is not None:
                    humidity_data.append(result.hourly.relative_humidity_2m[i])
                else:
                    humidity_data.append(None)
                
                if i < len(result.hourly.dew_point_2m) and result.hourly.dew_point_2m[i] is not None:
                    dew_point_data.append(result.hourly.dew_point_2m[i])
                else:
                    dew_point_data.append(None)
        
        if comfort_times:
            # Create dual-axis chart for humidity and dew point
            fig = go.Figure()
            
            # Add humidity line
            fig.add_trace(go.Scatter(
                x=comfort_times,
                y=humidity_data,
                mode='lines+markers',
                name='Humidity (%)',
                line=dict(color='blue', width=3),
                marker=dict(size=6),
                yaxis='y'
            ))
            
            # Add dew point line
            fig.add_trace(go.Scatter(
                x=comfort_times,
                y=dew_point_data,
                mode='lines+markers',
                name='Dew Point (°C)',
                line=dict(color='green', width=3),
                marker=dict(size=6),
                yaxis='y2'
            ))
            
            # Add comfort zones
            fig.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Comfortable humidity")
            fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="High humidity")
            
            fig.update_layout(
                title=f"Humidity & Comfort for {target_date.strftime('%A, %B %d, %Y')}",
                xaxis_title="Time",
                yaxis=dict(
                    title="Humidity (%)",
                    side="left",
                    color="blue",
                    range=[0, 100]
                ),
                yaxis2=dict(
                    title="Dew Point (°C)",
                    side="right",
                    overlaying="y",
                    color="green"
                ),
                hovermode='x unified',
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig, width='stretch')
    
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
        
        st.plotly_chart(fig, width='stretch')
    
    # Wind direction (simplified)
    if result.hourly.wind_direction_10m:
        st.subheader("Wind Direction")
        
        # Get wind directions for the time window
        wind_direction_stats = get_daypart_stats(
            result.hourly.time,
            result.hourly.wind_direction_10m,
            result.inputs.date,
            result.inputs.time_window,
            result.timezone
        )
        
        # Get the actual filtered data using slice_hourly_data_for_window
        from app.core.timeutil import slice_hourly_data_for_window
        filtered_times, filtered_directions = slice_hourly_data_for_window(
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
                
                # Add wind direction chart
                st.subheader("Wind Direction Over Time")
                
                # Get wind direction data for the selected date
                target_date = result.inputs.date
                wind_times = []
                wind_directions = []
                
                for i, dt in enumerate(result.hourly.time):
                    if dt and dt.date() == target_date and i < len(result.hourly.wind_direction_10m):
                        if result.hourly.wind_direction_10m[i] is not None:
                            wind_times.append(dt.strftime("%H:%M"))
                            wind_directions.append(result.hourly.wind_direction_10m[i])
                
                if wind_times:
                    # Create wind direction chart
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=wind_times,
                        y=wind_directions,
                        mode='lines+markers',
                        name='Wind Direction',
                        line=dict(color='purple', width=2),
                        marker=dict(size=6)
                    ))
                    
                    # Add compass direction annotations
                    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="N")
                    fig.add_hline(y=90, line_dash="dash", line_color="gray", annotation_text="E")
                    fig.add_hline(y=180, line_dash="dash", line_color="gray", annotation_text="S")
                    fig.add_hline(y=270, line_dash="dash", line_color="gray", annotation_text="W")
                    
                    fig.update_layout(
                        title=f"Wind Direction for {target_date.strftime('%A, %B %d, %Y')}",
                        xaxis_title="Time",
                        yaxis_title="Wind Direction (degrees)",
                        yaxis=dict(range=[0, 360]),
                        height=400
                    )
                    
                    st.plotly_chart(fig, width='stretch')
    
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
        
        st.plotly_chart(fig, width='stretch')
    
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


def display_pressure_tab(result: UnifiedResult):
    """Display pressure and atmospheric conditions tab."""
    
    st.subheader("Atmospheric Pressure & Conditions")
    
    if not result.hourly:
        st.warning("Hourly data not available.")
        return
    
    # Current pressure
    if result.current_openmeteo and result.current_openmeteo.surface_pressure:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Surface Pressure", f"{result.current_openmeteo.surface_pressure:.1f} hPa")
        with col2:
            if result.current_openmeteo.dew_point_2m:
                st.metric("Dew Point", f"{result.current_openmeteo.dew_point_2m:.1f}°C")
        with col3:
            if result.current_openmeteo.visibility:
                st.metric("Visibility", f"{result.current_openmeteo.visibility/1000:.1f} km")
    else:
        st.info("Pressure data not available in current API response. This feature requires additional API parameters.")
    
    # Pressure chart
    if result.hourly.surface_pressure:
        valid_pressure = [(t, p) for t, p in zip(result.hourly.time, result.hourly.surface_pressure) if p is not None]
        if valid_pressure:
            times, pressures = zip(*valid_pressure)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=times,
                y=pressures,
                mode='lines+markers',
                name='Surface Pressure',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            ))
            
            fig.update_layout(
                title="Atmospheric Pressure Over Time",
                xaxis_title="Time",
                yaxis_title="Pressure (hPa)",
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig, width='stretch')
    
    # Pressure statistics
    if result.hourly.surface_pressure:
        valid_pressures = [p for p in result.hourly.surface_pressure if p is not None]
        if valid_pressures:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Min Pressure", f"{min(valid_pressures):.1f} hPa")
            with col2:
                st.metric("Max Pressure", f"{max(valid_pressures):.1f} hPa")
            with col3:
                st.metric("Avg Pressure", f"{sum(valid_pressures)/len(valid_pressures):.1f} hPa")
            with col4:
                pressure_range = max(valid_pressures) - min(valid_pressures)
                st.metric("Pressure Range", f"{pressure_range:.1f} hPa")
    
    # Dew point and humidity relationship
    if result.hourly.dew_point_2m and result.hourly.temperature_2m:
        st.subheader("Temperature vs Dew Point")
        
        valid_data = [(t, temp, dew) for t, temp, dew in zip(result.hourly.time, result.hourly.temperature_2m, result.hourly.dew_point_2m) 
                     if temp is not None and dew is not None]
        
        if valid_data:
            times, temps, dews = zip(*valid_data)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=times,
                y=temps,
                mode='lines+markers',
                name='Temperature',
                line=dict(color='red', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=times,
                y=dews,
                mode='lines+markers',
                name='Dew Point',
                line=dict(color='blue', width=2)
            ))
            
            fig.update_layout(
                title="Temperature vs Dew Point",
                xaxis_title="Time",
                yaxis_title="Temperature (°C)",
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig, width='stretch')
            
            # Comfort analysis
            temp_dew_diff = [t - d for t, d in zip(temps, dews) if t is not None and d is not None]
            if temp_dew_diff:
                avg_diff = sum(temp_dew_diff) / len(temp_dew_diff)
                if avg_diff < 2:
                    st.warning("⚠️ High humidity conditions - very uncomfortable")
                elif avg_diff < 4:
                    st.info("💧 High humidity - somewhat uncomfortable")
                else:
                    st.success("✅ Comfortable humidity levels")


def display_advanced_tab(result: UnifiedResult):
    """Display advanced weather parameters tab."""
    
    st.subheader("Advanced Weather Parameters")
    
    if not result.hourly:
        st.warning("Hourly data not available.")
        return
    
    st.info("🔧 Advanced parameters (pressure, evapotranspiration, detailed precipitation) require additional API parameters. Currently showing basic weather data.")
    
    # Evapotranspiration
    if result.hourly.evapotranspiration:
        st.subheader("Evapotranspiration")
        valid_et = [(t, et) for t, et in zip(result.hourly.time, result.hourly.evapotranspiration) if et is not None]
        if valid_et:
            times, et_values = zip(*valid_et)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=times,
                y=et_values,
                mode='lines+markers',
                name='Evapotranspiration',
                line=dict(color='green', width=2),
                fill='tonexty'
            ))
            
            fig.update_layout(
                title="Evapotranspiration Rate",
                xaxis_title="Time",
                yaxis_title="ET (mm)",
                hovermode='x unified',
                height=300
            )
            
            st.plotly_chart(fig, width='stretch')
    
    # Vapour Pressure Deficit
    if result.hourly.vapour_pressure_deficit:
        st.subheader("Vapour Pressure Deficit")
        valid_vpd = [(t, vpd) for t, vpd in zip(result.hourly.time, result.hourly.vapour_pressure_deficit) if vpd is not None]
        if valid_vpd:
            times, vpd_values = zip(*valid_vpd)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=times,
                y=vpd_values,
                mode='lines+markers',
                name='VPD',
                line=dict(color='purple', width=2)
            ))
            
            fig.update_layout(
                title="Vapour Pressure Deficit",
                xaxis_title="Time",
                yaxis_title="VPD (kPa)",
                hovermode='x unified',
                height=300
            )
            
            st.plotly_chart(fig, width='stretch')
    
    # Detailed precipitation breakdown
    if result.hourly.rain or result.hourly.showers or result.hourly.snowfall:
        st.subheader("Precipitation Breakdown")
        
        # Create precipitation breakdown chart
        times = result.hourly.time
        
        fig = go.Figure()
        
        if result.hourly.rain:
            valid_rain = [r if r is not None else 0 for r in result.hourly.rain]
            fig.add_trace(go.Bar(
                x=times,
                y=valid_rain,
                name='Rain',
                marker_color='blue',
                opacity=0.7
            ))
        
        if result.hourly.showers:
            valid_showers = [s if s is not None else 0 for s in result.hourly.showers]
            fig.add_trace(go.Bar(
                x=times,
                y=valid_showers,
                name='Showers',
                marker_color='lightblue',
                opacity=0.7
            ))
        
        if result.hourly.snowfall:
            valid_snow = [s if s is not None else 0 for s in result.hourly.snowfall]
            fig.add_trace(go.Bar(
                x=times,
                y=valid_snow,
                name='Snowfall',
                marker_color='white',
                opacity=0.7
            ))
        
        fig.update_layout(
            title="Precipitation Breakdown by Type",
            xaxis_title="Time",
            yaxis_title="Precipitation (mm)",
            barmode='stack',
            height=400
        )
        
        st.plotly_chart(fig, width='stretch')
    
    # Cloud cover layers
    if result.hourly.cloud_cover_low or result.hourly.cloud_cover_mid or result.hourly.cloud_cover_high:
        st.subheader("Cloud Cover Layers")
        
        times = result.hourly.time
        
        fig = go.Figure()
        
        if result.hourly.cloud_cover_low:
            valid_low = [c if c is not None else 0 for c in result.hourly.cloud_cover_low]
            fig.add_trace(go.Scatter(
                x=times,
                y=valid_low,
                mode='lines',
                name='Low Clouds',
                line=dict(color='lightgray', width=2),
                fill='tonexty'
            ))
        
        if result.hourly.cloud_cover_mid:
            valid_mid = [c if c is not None else 0 for c in result.hourly.cloud_cover_mid]
            fig.add_trace(go.Scatter(
                x=times,
                y=valid_mid,
                mode='lines',
                name='Mid Clouds',
                line=dict(color='gray', width=2),
                fill='tonexty'
            ))
        
        if result.hourly.cloud_cover_high:
            valid_high = [c if c is not None else 0 for c in result.hourly.cloud_cover_high]
            fig.add_trace(go.Scatter(
                x=times,
                y=valid_high,
                mode='lines',
                name='High Clouds',
                line=dict(color='darkgray', width=2),
                fill='tonexty'
            ))
        
        fig.update_layout(
            title="Cloud Cover by Altitude",
            xaxis_title="Time",
            yaxis_title="Cloud Cover (%)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, width='stretch')
    
    # Data availability summary
    st.subheader("Data Availability")
    
    data_summary = {
        "Parameter": ["Temperature", "Precipitation", "Wind", "Humidity", "Pressure", "Visibility", 
                     "Evapotranspiration", "VPD", "Rain", "Showers", "Snowfall", "Low Clouds", "Mid Clouds", "High Clouds"],
        "Available": [
            "✅" if result.hourly.temperature_2m else "❌",
            "✅" if result.hourly.precipitation else "❌",
            "✅" if result.hourly.wind_speed_10m else "❌",
            "✅" if result.hourly.relative_humidity_2m else "❌",
            "✅" if result.hourly.surface_pressure else "❌",
            "✅" if result.hourly.visibility else "❌",
            "✅" if result.hourly.evapotranspiration else "❌",
            "✅" if result.hourly.vapour_pressure_deficit else "❌",
            "✅" if result.hourly.rain else "❌",
            "✅" if result.hourly.showers else "❌",
            "✅" if result.hourly.snowfall else "❌",
            "✅" if result.hourly.cloud_cover_low else "❌",
            "✅" if result.hourly.cloud_cover_mid else "❌",
            "✅" if result.hourly.cloud_cover_high else "❌"
        ]
    }
    
    df = pd.DataFrame(data_summary)
    st.dataframe(df, width='stretch')


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
        st.dataframe(df, width='stretch')


def display_map_tab(result: UnifiedResult):
    """Display map tab."""
    
    if not result.geocode:
        st.warning("Location data not available.")
        return
    
    st.subheader("Location Map")
    
    # Create a simple map using Streamlit's built-in map
    map_data = pd.DataFrame({
        'lat': [result.geocode.lat],
        'lon': [result.geocode.lon],
        'name': [result.geocode.formatted_address]
    })
    
    # Display the map
    st.map(map_data, zoom=11)
    
    # Add location details below the map
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📍 Location Details**")
        st.write(f"**Address:** {result.geocode.formatted_address}")
        st.write(f"**Coordinates:** {result.geocode.lat:.4f}°, {result.geocode.lon:.4f}°")
        st.write(f"**Date:** {result.inputs.date.strftime('%A, %B %d, %Y')}")
        st.write(f"**Time Window:** {result.inputs.time_window} ({format_time_window_display(result.inputs.time_window)})")
    
    with col2:
        st.markdown("**🌍 Geographic Info**")
        st.write(f"**Timezone:** {result.timezone}")
        if result.current_openmeteo and result.current_openmeteo.temperature_2m:
            st.write(f"**Current Temperature:** {result.current_openmeteo.temperature_2m:.1f}°C")
        if result.current_openmeteo and result.current_openmeteo.precipitation:
            st.write(f"**Current Precipitation:** {result.current_openmeteo.precipitation:.1f} mm")
    
    # Try to also show the pydeck map as an alternative
    st.markdown("---")
    st.markdown("**🗺️ Interactive Map (Alternative View)**")
    
    try:
        # Create pydeck map
        deck = create_paradeguard_map(
            lat=result.geocode.lat,
            lon=result.geocode.lon,
            address=result.geocode.formatted_address,
            date=result.inputs.date.strftime("%Y-%m-%d"),
            time_window=result.inputs.time_window
        )
        
        st.pydeck_chart(deck, width='stretch')
    except Exception as e:
        st.info("Interactive map view is not available. The simple map above shows the location.")
        st.write(f"*Note: {str(e)}*")


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
            width='stretch'
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
            width='stretch'
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
