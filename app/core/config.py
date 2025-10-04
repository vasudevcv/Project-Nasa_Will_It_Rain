"""
Configuration and secrets management.
"""
import os
import streamlit as st
from dotenv import load_dotenv


def load_secrets():
    """Load secrets from environment variables or Streamlit secrets."""
    # Load .env file for local development
    load_dotenv()
    
    # Try to get from Streamlit secrets first (production)
    try:
        secrets = st.secrets
        return {
            "GOOGLE_MAPS_API_KEY": secrets.get("GOOGLE_MAPS_API_KEY"),
            "GOOGLE_WEATHER_API_KEY": secrets.get("GOOGLE_WEATHER_API_KEY"),
            "RAPIDAPI_KEY": secrets.get("RAPIDAPI_KEY")
        }
    except Exception:
        # Fall back to environment variables (development)
        return {
            "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY"),
            "GOOGLE_WEATHER_API_KEY": os.getenv("GOOGLE_WEATHER_API_KEY"),
            "RAPIDAPI_KEY": os.getenv("RAPIDAPI_KEY")
        }


def get_api_key(service: str) -> str:
    """Get API key for a specific service."""
    secrets = load_secrets()
    key = secrets.get(service)
    
    if not key:
        raise ValueError(f"API key for {service} not found. Please check your environment variables or Streamlit secrets.")
    
    return key


def validate_secrets() -> tuple[bool, list[str]]:
    """Validate that all required secrets are available."""
    secrets = load_secrets()
    missing = []
    
    required_keys = ["GOOGLE_MAPS_API_KEY", "GOOGLE_WEATHER_API_KEY", "RAPIDAPI_KEY"]
    
    for key in required_keys:
        if not secrets.get(key):
            missing.append(key)
    
    return len(missing) == 0, missing
