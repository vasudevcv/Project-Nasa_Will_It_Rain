"""
Map utilities for pydeck visualization.
"""
import pydeck as pdk
from typing import Tuple, Optional, Dict, Any


def create_location_pin_layer(
    lat: float, 
    lon: float, 
    address: str,
    date: str,
    time_window: str
) -> pdk.Layer:
    """Create a pin layer for the location."""
    
    # Define the pin data
    pin_data = [{
        "coordinates": [lon, lat],
        "address": address,
        "date": date,
        "time_window": time_window
    }]
    
    # Create the pin layer
    pin_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pin_data,
        get_position="coordinates",
        get_color=[255, 0, 0, 200],  # Red color with transparency
        get_radius=100,  # Radius in meters
        pickable=True,
        auto_highlight=True,
    )
    
    return pin_layer


def create_area_of_interest_layer(
    lat: float, 
    lon: float, 
    radius_km: float = 5.0
) -> pdk.Layer:
    """Create a translucent circle for area of interest."""
    
    # Convert km to approximate degrees (rough approximation)
    radius_deg = radius_km / 111.0  # 1 degree ≈ 111 km
    
    # Create a simple circle approximation with a polygon
    import math
    
    # Generate points for a circle
    points = []
    for i in range(36):  # 36 points for a smooth circle
        angle = i * 10  # 10 degrees per point
        x = lon + radius_deg * math.cos(math.radians(angle))
        y = lat + radius_deg * math.sin(math.radians(angle))
        points.append([x, y])
    
    # Close the polygon
    points.append(points[0])
    
    circle_data = [{
        "coordinates": points
    }]
    
    circle_layer = pdk.Layer(
        "PolygonLayer",
        data=circle_data,
        get_polygon="coordinates",
        get_fill_color=[0, 100, 200, 50],  # Blue with low transparency
        get_line_color=[0, 100, 200, 150],  # Blue with higher transparency for border
        line_width_min_pixels=2,
        pickable=False,
    )
    
    return circle_layer


def create_map_view(
    lat: float, 
    lon: float, 
    zoom: int = 11,
    pitch: int = 0,
    bearing: int = 0
) -> pdk.ViewState:
    """Create a map view state."""
    return pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=zoom,
        pitch=pitch,
        bearing=bearing
    )


def create_tooltip_html(address: str, date: str, time_window: str) -> Dict[str, str]:
    """Create HTML tooltip for the map."""
    return {
        "html": f"""
        <div style="padding: 10px; background-color: white; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4 style="margin: 0 0 5px 0; color: #333;">{address}</h4>
            <p style="margin: 0; color: #666; font-size: 12px;">Date: {date}</p>
            <p style="margin: 0; color: #666; font-size: 12px;">Time: {time_window}</p>
        </div>
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black"
        }
    }


def create_paradeguard_map(
    lat: float,
    lon: float,
    address: str,
    date: str,
    time_window: str,
    show_area_of_interest: bool = True,
    radius_km: float = 5.0
) -> pdk.Deck:
    """Create a complete pydeck map for ParadeGuard."""
    
    # Create layers
    layers = []
    
    # Add area of interest layer if requested
    if show_area_of_interest:
        area_layer = create_area_of_interest_layer(lat, lon, radius_km)
        layers.append(area_layer)
    
    # Add location pin layer
    pin_layer = create_location_pin_layer(lat, lon, address, date, time_window)
    layers.append(pin_layer)
    
    # Create view state
    view_state = create_map_view(lat, lon)
    
    # Create tooltip
    tooltip = create_tooltip_html(address, date, time_window)
    
    # Create the deck with a default map style that doesn't require API key
    deck = pdk.Deck(
        map_style=None,  # Use default map style
        initial_view_state=view_state,
        layers=layers,
        tooltip=tooltip
    )
    
    return deck


def get_map_style_options() -> Dict[str, str]:
    """Get available map style options."""
    return {
        "Light": "mapbox://styles/mapbox/light-v10",
        "Dark": "mapbox://styles/mapbox/dark-v10",
        "Satellite": "mapbox://styles/mapbox/satellite-v9",
        "Streets": "mapbox://styles/mapbox/streets-v11",
        "Outdoors": "mapbox://styles/mapbox/outdoors-v11"
    }
