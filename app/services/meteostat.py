"""
Meteostat API service for historical climatology data.
"""
import httpx
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional, List
from datetime import datetime, date
import logging
import statistics

from app.core.schemas import MeteostatData, MeteostatMonthlyRow
from app.core.config import get_api_key

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
)
@st.cache_data(ttl=86400, show_spinner=False)  # Cache for 24 hours
def get_monthly_climatology(
    lat: float, 
    lon: float, 
    start_year: int = 2015, 
    end_year: int = 2024,
    alt: Optional[float] = None
) -> Optional[MeteostatData]:
    """
    Get monthly climatology data from Meteostat API.
    
    Args:
        lat: Latitude
        lon: Longitude
        start_year: Start year for historical data
        end_year: End year for historical data
        alt: Altitude in meters (optional)
        
    Returns:
        MeteostatData with monthly climatology and percentiles
        None if error occurred
    """
    try:
        api_key = get_api_key("RAPIDAPI_KEY")
        
        url = "https://meteostat.p.rapidapi.com/point/monthly"
        
        params = {
            "lat": lat,
            "lon": lon,
            "start": f"{start_year}-01-01",
            "end": f"{end_year}-12-31"
        }
        
        if alt is not None:
            params["alt"] = alt
        
        headers = {
            "x-rapidapi-host": "meteostat.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        
        logger.info(f"Fetching monthly climatology for {lat}, {lon} ({start_year}-{end_year})")
        
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the response
            monthly_data = data.get("data", [])
            
            if not monthly_data:
                logger.warning("No monthly climatology data available")
                return None
            
            # Convert to our schema
            rows = []
            for item in monthly_data:
                row = MeteostatMonthlyRow(
                    date=item.get("date", ""),
                    tavg=item.get("tavg"),
                    tmin=item.get("tmin"),
                    tmax=item.get("tmax"),
                    prcp=item.get("prcp"),
                    tsun=item.get("tsun"),
                    pres=item.get("pres")
                )
                rows.append(row)
            
            # Calculate percentiles for the target month
            target_month = datetime.now().month
            month_percentile_rain = calculate_month_percentile(rows, target_month, "prcp")
            month_percentile_temp = calculate_month_percentile(rows, target_month, "tavg")
            
            meteostat_result = MeteostatData(
                data=rows,
                month_percentile_rain=month_percentile_rain,
                month_percentile_temp=month_percentile_temp
            )
            
            logger.info(f"Successfully fetched {len(rows)} monthly records from Meteostat")
            return meteostat_result
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during Meteostat fetch: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error during Meteostat fetch: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during Meteostat fetch: {e}")
        return None


def calculate_month_percentile(
    rows: List[MeteostatMonthlyRow], 
    target_month: int, 
    field: str
) -> Optional[float]:
    """
    Calculate percentile for a specific month and field.
    
    Args:
        rows: List of monthly data rows
        target_month: Target month (1-12)
        field: Field name ('prcp' or 'tavg')
        
    Returns:
        Percentile value (0-100) or None if insufficient data
    """
    try:
        # Filter data for the target month
        month_data = []
        for row in rows:
            try:
                row_date = datetime.strptime(row.date, "%Y-%m-%d")
                if row_date.month == target_month:
                    value = getattr(row, field, None)
                    if value is not None:
                        month_data.append(value)
            except (ValueError, AttributeError):
                continue
        
        if len(month_data) < 3:  # Need at least 3 data points
            return None
        
        # Calculate percentile (simplified - using median as 50th percentile)
        # In a more sophisticated implementation, you'd calculate actual percentiles
        median_value = statistics.median(month_data)
        mean_value = statistics.mean(month_data)
        
        # Simple percentile estimation based on current year's value vs historical
        # This is a simplified approach - in production you'd want more sophisticated percentile calculation
        current_year = datetime.now().year
        current_value = None
        
        for row in rows:
            try:
                row_date = datetime.strptime(row.date, "%Y-%m-%d")
                if row_date.year == current_year and row_date.month == target_month:
                    current_value = getattr(row, field, None)
                    break
            except (ValueError, AttributeError):
                continue
        
        if current_value is None:
            return None
        
        # Calculate approximate percentile
        if field == "prcp":
            # For precipitation, higher values = higher percentile
            if current_value >= median_value:
                percentile = 50 + min((current_value - median_value) / (max(month_data) - median_value) * 50, 50)
            else:
                percentile = max((current_value - min(month_data)) / (median_value - min(month_data)) * 50, 0)
        else:
            # For temperature, use similar logic
            if current_value >= median_value:
                percentile = 50 + min((current_value - median_value) / (max(month_data) - median_value) * 50, 50)
            else:
                percentile = max((current_value - min(month_data)) / (median_value - min(month_data)) * 50, 0)
        
        return round(percentile, 1)
        
    except Exception as e:
        logger.error(f"Error calculating percentile for {field}: {e}")
        return None


def validate_meteostat_result(result: Optional[MeteostatData]) -> tuple[bool, str]:
    """
    Validate a Meteostat result.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if result is None:
        return False, "Unable to fetch historical climatology data."
    
    if not result.data:
        return False, "No historical data available for this location."
    
    return True, ""
