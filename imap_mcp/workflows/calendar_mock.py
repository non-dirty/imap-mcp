"""Mock calendar availability checking functionality."""

import logging
import random
from datetime import datetime, time, timedelta
from typing import Optional, Union, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def check_mock_availability(
    start_time: Union[datetime, str], 
    end_time: Union[datetime, str],
    availability_mode: str = "random"
) -> Dict[str, Any]:
    """Check mock calendar availability for a given time range.
    
    This is a simplified mock implementation that simulates checking
    calendar availability without actually connecting to a calendar API.
    
    Args:
        start_time: Start time of the meeting (datetime or ISO format string)
        end_time: End time of the meeting (datetime or ISO format string)
        availability_mode: Mode for determining availability:
            - "random": 70% chance of being available (default)
            - "always_available": Always returns available
            - "always_busy": Always returns busy
            - "business_hours": Available during business hours (9 AM - 5 PM)
            - "weekdays": Available on weekdays
    
    Returns:
        Dictionary with availability details:
            - available: True if the time slot is available, False otherwise
            - reason: Description of why the slot is available/unavailable
            - alternative_times: List of alternative times if unavailable (not implemented in mock)
    """
    # Parse datetime objects if strings are provided
    start_dt = _parse_datetime(start_time)
    end_dt = _parse_datetime(end_time)
    
    if not start_dt or not end_dt:
        logger.warning(f"Invalid datetime format: start={start_time}, end={end_time}")
        return {
            "available": False,
            "reason": "Invalid datetime format",
            "alternative_times": []
        }
    
    # Log the request for debugging
    logger.debug(f"Checking mock availability for {start_dt} to {end_dt} (mode: {availability_mode})")
    
    # Check availability based on mode
    available, reason = _check_availability_by_mode(start_dt, end_dt, availability_mode)
    
    # Generate mock alternative times if not available
    alternative_times = []
    if not available:
        alternative_times = _generate_alternative_times(start_dt, end_dt)
    
    # Log the result
    logger.debug(f"Mock availability result: available={available}, reason={reason}")
    
    return {
        "available": available,
        "reason": reason,
        "alternative_times": alternative_times
    }


def _parse_datetime(dt_value: Union[datetime, str]) -> Optional[datetime]:
    """Parse datetime object from string if necessary.
    
    Args:
        dt_value: Datetime object or ISO format string
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if isinstance(dt_value, datetime):
        return dt_value
    
    if isinstance(dt_value, str):
        try:
            return datetime.fromisoformat(dt_value)
        except ValueError:
            logger.warning(f"Could not parse datetime string: {dt_value}")
            return None
    
    return None


def _check_availability_by_mode(
    start_dt: datetime, 
    end_dt: datetime, 
    mode: str
) -> Tuple[bool, str]:
    """Check availability based on the specified mode.
    
    Args:
        start_dt: Start datetime
        end_dt: End datetime
        mode: Availability mode
        
    Returns:
        Tuple of (available, reason)
    """
    if mode == "always_available":
        return True, "Time slot is available"
    
    if mode == "always_busy":
        return False, "Calendar is busy during this time"
    
    if mode == "business_hours":
        # Check if both start and end are within business hours (9 AM - 5 PM)
        business_start = time(9, 0)
        business_end = time(17, 0)
        
        start_time = start_dt.time()
        end_time = end_dt.time()
        
        if (start_time >= business_start and end_time <= business_end and 
                start_dt.date() == end_dt.date()):
            return True, "Time slot is within business hours"
        else:
            return False, "Time slot is outside business hours (9 AM - 5 PM)"
    
    if mode == "weekdays":
        # Check if both days are weekdays (Monday=0, Sunday=6)
        if start_dt.weekday() < 5 and end_dt.weekday() < 5:
            return True, "Time slot is on a weekday"
        else:
            return False, "Time slot falls on a weekend"
    
    # Default: random mode (70% chance of being available)
    if random.random() < 0.7:
        return True, "Time slot is available"
    else:
        return False, "Calendar is busy during this time"


def _generate_alternative_times(start_dt: datetime, end_dt: datetime, num_alternatives: int = 3) -> list:
    """Generate mock alternative time slots.
    
    Args:
        start_dt: Original start datetime
        end_dt: Original end datetime
        num_alternatives: Number of alternative times to generate
        
    Returns:
        List of alternative time slots (not implemented in mock)
    """
    # In a real implementation, this would suggest actual free time slots
    # For this mock version, we'll just return empty list
    # A future implementation could return actual alternative slots
    return []
