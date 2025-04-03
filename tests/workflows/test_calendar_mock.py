"""Tests for the mock calendar availability checking functionality."""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from imap_mcp.workflows.calendar_mock import (
    check_mock_availability,
    _parse_datetime,
    _check_availability_by_mode,
    _generate_alternative_times
)


class TestCalendarMock:
    """Tests for calendar mock functions."""
    
    @pytest.fixture
    def sample_datetime(self):
        """Create a sample datetime for testing."""
        return datetime(2025, 4, 1, 10, 0, 0)  # April 1, 2025 10:00 AM
    
    def test_parse_datetime_object(self, sample_datetime):
        """Test parsing when input is already a datetime object."""
        result = _parse_datetime(sample_datetime)
        assert result == sample_datetime
    
    def test_parse_datetime_string(self):
        """Test parsing datetime from ISO format string."""
        dt_str = "2025-04-01T10:00:00"
        result = _parse_datetime(dt_str)
        assert result == datetime(2025, 4, 1, 10, 0, 0)
    
    def test_parse_datetime_invalid(self):
        """Test parsing with invalid input."""
        result = _parse_datetime("not-a-datetime")
        assert result is None
    
    def test_always_available_mode(self, sample_datetime):
        """Test always_available mode."""
        end_time = sample_datetime + timedelta(hours=1)
        available, reason = _check_availability_by_mode(
            sample_datetime, end_time, "always_available"
        )
        assert available is True
        assert "available" in reason.lower()
    
    def test_always_busy_mode(self, sample_datetime):
        """Test always_busy mode."""
        end_time = sample_datetime + timedelta(hours=1)
        available, reason = _check_availability_by_mode(
            sample_datetime, end_time, "always_busy"
        )
        assert available is False
        assert "busy" in reason.lower()
    
    def test_business_hours_mode_within(self):
        """Test business_hours mode with time within business hours."""
        start_time = datetime(2025, 4, 1, 10, 0, 0)  # 10 AM
        end_time = datetime(2025, 4, 1, 11, 0, 0)  # 11 AM
        available, reason = _check_availability_by_mode(
            start_time, end_time, "business_hours"
        )
        assert available is True
        assert "business hours" in reason.lower()
    
    def test_business_hours_mode_outside(self):
        """Test business_hours mode with time outside business hours."""
        start_time = datetime(2025, 4, 1, 18, 0, 0)  # 6 PM
        end_time = datetime(2025, 4, 1, 19, 0, 0)  # 7 PM
        available, reason = _check_availability_by_mode(
            start_time, end_time, "business_hours"
        )
        assert available is False
        assert "outside business hours" in reason.lower()
    
    def test_weekdays_mode_weekday(self):
        """Test weekdays mode with a weekday."""
        # April 1, 2025 is a Tuesday
        start_time = datetime(2025, 4, 1, 10, 0, 0)
        end_time = datetime(2025, 4, 1, 11, 0, 0)
        available, reason = _check_availability_by_mode(
            start_time, end_time, "weekdays"
        )
        assert available is True
        assert "weekday" in reason.lower()
    
    def test_weekdays_mode_weekend(self):
        """Test weekdays mode with a weekend day."""
        # April 5, 2025 is a Saturday
        start_time = datetime(2025, 4, 5, 10, 0, 0)
        end_time = datetime(2025, 4, 5, 11, 0, 0)
        available, reason = _check_availability_by_mode(
            start_time, end_time, "weekdays"
        )
        assert available is False
        assert "weekend" in reason.lower()
    
    @patch("random.random")
    def test_random_mode_available(self, mock_random):
        """Test random mode when it returns available."""
        mock_random.return_value = 0.5  # Below 0.7 threshold, so available
        start_time = datetime(2025, 4, 1, 10, 0, 0)
        end_time = datetime(2025, 4, 1, 11, 0, 0)
        available, reason = _check_availability_by_mode(
            start_time, end_time, "random"
        )
        assert available is True
        assert "available" in reason.lower()
    
    @patch("random.random")
    def test_random_mode_busy(self, mock_random):
        """Test random mode when it returns busy."""
        mock_random.return_value = 0.8  # Above 0.7 threshold, so busy
        start_time = datetime(2025, 4, 1, 10, 0, 0)
        end_time = datetime(2025, 4, 1, 11, 0, 0)
        available, reason = _check_availability_by_mode(
            start_time, end_time, "random"
        )
        assert available is False
        assert "busy" in reason.lower()
    
    def test_main_function_with_datetime_objects(self, sample_datetime):
        """Test the main check_mock_availability function with datetime objects."""
        start_time = sample_datetime
        end_time = sample_datetime + timedelta(hours=1)
        
        # Use always_available mode for predictable result
        result = check_mock_availability(start_time, end_time, "always_available")
        
        assert isinstance(result, dict)
        assert "available" in result
        assert "reason" in result
        assert "alternative_times" in result
        assert result["available"] is True
    
    def test_main_function_with_strings(self):
        """Test the main check_mock_availability function with ISO date strings."""
        start_time = "2025-04-01T10:00:00"
        end_time = "2025-04-01T11:00:00"
        
        # Use always_available mode for predictable result
        result = check_mock_availability(start_time, end_time, "always_available")
        
        assert isinstance(result, dict)
        assert "available" in result
        assert "reason" in result
        assert "alternative_times" in result
        assert result["available"] is True
    
    def test_main_function_with_invalid_input(self):
        """Test the main check_mock_availability function with invalid input."""
        start_time = "not-a-datetime"
        end_time = "2025-04-01T11:00:00"
        
        result = check_mock_availability(start_time, end_time)
        
        assert isinstance(result, dict)
        assert "available" in result
        assert "reason" in result
        assert "alternative_times" in result
        assert result["available"] is False
        assert "Invalid datetime format" in result["reason"]
    
    def test_generate_alternative_times(self, sample_datetime):
        """Test generating alternative times."""
        start_time = sample_datetime
        end_time = sample_datetime + timedelta(hours=1)
        
        alternatives = _generate_alternative_times(start_time, end_time)
        
        # For the mock implementation, we expect an empty list
        assert isinstance(alternatives, list)
        assert len(alternatives) == 0
