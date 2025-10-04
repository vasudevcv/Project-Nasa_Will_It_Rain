"""
Time zone handling and time window utilities.
"""
from datetime import datetime, time, timedelta
from typing import List, Tuple, Optional
import pytz


# Time window definitions
EVENING_START = time(18, 0)  # 18:00
EVENING_END = time(21, 0)    # 21:00
MORNING_START = time(6, 0)   # 06:00
MORNING_END = time(12, 0)    # 12:00
AFTERNOON_START = time(12, 0)  # 12:00
AFTERNOON_END = time(18, 0)    # 18:00
NIGHT_START = time(21, 0)    # 21:00
NIGHT_END = time(6, 0)       # 06:00 (next day)


def get_time_window_bounds(time_window: str) -> Tuple[time, time]:
    """Get start and end times for a given time window."""
    windows = {
        "Morning": (MORNING_START, MORNING_END),
        "Afternoon": (AFTERNOON_START, AFTERNOON_END),
        "Evening": (EVENING_START, EVENING_END),
        "Night": (NIGHT_START, NIGHT_END),
    }
    return windows.get(time_window, (EVENING_START, EVENING_END))


def normalize_to_local_timezone(dt: datetime, timezone_str: str) -> datetime:
    """Convert datetime to local timezone."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=pytz.UTC)
    
    local_tz = pytz.timezone(timezone_str)
    return dt.astimezone(local_tz)


def slice_hourly_data_for_window(
    times: List[datetime], 
    data: List[Optional[float]], 
    target_date: datetime, 
    time_window: str,
    timezone_str: str
) -> Tuple[List[datetime], List[Optional[float]]]:
    """Slice hourly data for a specific date and time window."""
    if not times or not data:
        return [], []
    
    # Normalize target date to local timezone
    local_tz = pytz.timezone(timezone_str)
    target_date_local = target_date.replace(tzinfo=local_tz)
    
    # Get time window bounds
    start_time, end_time = get_time_window_bounds(time_window)
    
    # Handle night window (spans midnight)
    if time_window == "Night":
        # Night spans from 21:00 to 06:00 next day
        start_datetime = target_date_local.replace(hour=start_time.hour, minute=start_time.minute)
        end_datetime = (target_date_local + timedelta(days=1)).replace(hour=end_time.hour, minute=end_time.minute)
    else:
        # Other windows are within the same day
        start_datetime = target_date_local.replace(hour=start_time.hour, minute=start_time.minute)
        end_datetime = target_date_local.replace(hour=end_time.hour, minute=end_time.minute)
    
    # Filter data within the time window
    filtered_times = []
    filtered_data = []
    
    for i, dt in enumerate(times):
        if dt >= start_datetime and dt < end_datetime:
            filtered_times.append(dt)
            if i < len(data):
                filtered_data.append(data[i])
            else:
                filtered_data.append(None)
    
    return filtered_times, filtered_data


def get_daypart_stats(
    times: List[datetime], 
    data: List[Optional[float]], 
    target_date: datetime, 
    time_window: str,
    timezone_str: str
) -> dict:
    """Get statistics for a specific daypart."""
    filtered_times, filtered_data = slice_hourly_data_for_window(
        times, data, target_date, time_window, timezone_str
    )
    
    if not filtered_data:
        return {
            "count": 0,
            "mean": None,
            "max": None,
            "min": None,
            "sum": None
        }
    
    # Filter out None values for calculations
    valid_data = [x for x in filtered_data if x is not None]
    
    if not valid_data:
        return {
            "count": len(filtered_data),
            "mean": None,
            "max": None,
            "min": None,
            "sum": None
        }
    
    return {
        "count": len(valid_data),
        "mean": sum(valid_data) / len(valid_data),
        "max": max(valid_data),
        "min": min(valid_data),
        "sum": sum(valid_data)
    }


def format_time_window_display(time_window: str) -> str:
    """Format time window for display."""
    windows = {
        "Morning": "06:00-12:00",
        "Afternoon": "12:00-18:00", 
        "Evening": "18:00-21:00",
        "Night": "21:00-06:00"
    }
    return windows.get(time_window, "18:00-21:00")


def get_timezone_from_coordinates(lat: float, lon: float) -> str:
    """Get timezone string from coordinates (simplified)."""
    # This is a simplified implementation
    # In production, you might want to use a more sophisticated timezone lookup
    # For now, we'll use a basic approximation based on longitude
    
    # Rough timezone estimation based on longitude
    # Each 15 degrees of longitude represents approximately 1 hour
    timezone_offset = int(lon / 15)
    
    # Common timezone mappings for major regions
    if 70 <= lon <= 90:  # India region
        return "Asia/Kolkata"
    elif 100 <= lon <= 120:  # Southeast Asia
        return "Asia/Singapore"
    elif 120 <= lon <= 140:  # East Asia
        return "Asia/Tokyo"
    elif -80 <= lon <= -70:  # Eastern US
        return "America/New_York"
    elif -120 <= lon <= -100:  # Western US
        return "America/Los_Angeles"
    else:
        # Default to UTC
        return "UTC"
