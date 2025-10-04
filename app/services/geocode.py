"""
Google Geocoding API service.
"""
import httpx
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional
import logging

from app.core.schemas import GeocodeResult
from app.core.config import get_api_key

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
)
@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def geocode_location(query: str) -> Optional[GeocodeResult]:
    """
    Geocode a location using Google Geocoding API.
    
    Args:
        query: Location query string (e.g., "Pathanamthitta, Kerala")
        
    Returns:
        GeocodeResult with address, lat, lon, and formatted_address
        None if no results found or error occurred
    """
    try:
        api_key = get_api_key("GOOGLE_MAPS_API_KEY")
        
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": query,
            "key": api_key
        }
        
        logger.info(f"Geocoding query: {query}")
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "OK":
                logger.warning(f"Geocoding API returned status: {data.get('status')}")
                return None
            
            results = data.get("results", [])
            if not results:
                logger.warning(f"No geocoding results found for: {query}")
                return None
            
            # Use the first result
            result = results[0]
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            
            geocode_result = GeocodeResult(
                address=query,
                lat=location.get("lat"),
                lon=location.get("lng"),
                formatted_address=result.get("formatted_address", query)
            )
            
            logger.info(f"Successfully geocoded: {geocode_result.formatted_address}")
            return geocode_result
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during geocoding: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error during geocoding: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during geocoding: {e}")
        return None


def validate_geocode_result(result: Optional[GeocodeResult]) -> tuple[bool, str]:
    """
    Validate a geocoding result.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if result is None:
        return False, "Location not found. Please try a broader location name or check spelling."
    
    if result.lat is None or result.lon is None:
        return False, "Invalid coordinates returned. Please try a different location."
    
    # Check for reasonable coordinate bounds
    if not (-90 <= result.lat <= 90) or not (-180 <= result.lon <= 180):
        return False, "Invalid coordinate values. Please try a different location."
    
    return True, ""
