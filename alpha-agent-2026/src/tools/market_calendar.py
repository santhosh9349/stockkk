"""Market calendar tool for holiday and event detection.

Implements market holiday detection and event scheduling.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MarketCalendar:
    """Market calendar for holiday and event detection.
    
    Loads NYSE holiday calendar and provides utility methods
    for market status checks.
    """
    
    def __init__(self, holidays_path: Optional[str] = None):
        """Initialize calendar with holidays file.
        
        Args:
            holidays_path: Path to NYSE holidays JSON file
        """
        self.holidays_path = holidays_path or str(
            Path(__file__).parent.parent.parent / "data" / "nyse_holidays_2026.json"
        )
        self._holidays: dict[str, str] = {}
        self._load_holidays()
    
    def _load_holidays(self) -> None:
        """Load holidays from JSON file."""
        try:
            with open(self.holidays_path, "r") as f:
                data = json.load(f)
                self._holidays = data.get("holidays", {})
                logger.debug(f"Loaded {len(self._holidays)} holidays")
        except FileNotFoundError:
            logger.warning(f"Holidays file not found: {self.holidays_path}")
            self._holidays = {}
        except Exception as e:
            logger.error(f"Failed to load holidays: {e}")
            self._holidays = {}
    
    def is_market_holiday(self, check_date: Optional[date] = None) -> bool:
        """Check if given date is a market holiday.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            True if market is closed for holiday
        """
        if check_date is None:
            check_date = date.today()
        
        date_str = check_date.isoformat()
        return date_str in self._holidays
    
    def get_holiday_name(self, check_date: Optional[date] = None) -> Optional[str]:
        """Get holiday name for a given date.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            Holiday name or None if not a holiday
        """
        if check_date is None:
            check_date = date.today()
        
        date_str = check_date.isoformat()
        return self._holidays.get(date_str)
    
    def is_weekend(self, check_date: Optional[date] = None) -> bool:
        """Check if given date is a weekend.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            True if Saturday or Sunday
        """
        if check_date is None:
            check_date = date.today()
        
        return check_date.weekday() >= 5  # Saturday=5, Sunday=6
    
    def is_market_open(self, check_date: Optional[date] = None) -> bool:
        """Check if market is open on given date.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            True if market is open
        """
        if check_date is None:
            check_date = date.today()
        
        if self.is_weekend(check_date):
            return False
        
        if self.is_market_holiday(check_date):
            return False
        
        return True
    
    def get_next_trading_day(self, from_date: Optional[date] = None) -> date:
        """Get the next trading day.
        
        Args:
            from_date: Starting date (defaults to today)
            
        Returns:
            Next date when market is open
        """
        if from_date is None:
            from_date = date.today()
        
        from datetime import timedelta
        check_date = from_date + timedelta(days=1)
        
        # Limit search to 10 days (covers long weekends)
        for _ in range(10):
            if self.is_market_open(check_date):
                return check_date
            check_date += timedelta(days=1)
        
        return check_date
    
    def get_market_status(self, check_date: Optional[date] = None) -> dict:
        """Get comprehensive market status.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            Dict with market status details
        """
        if check_date is None:
            check_date = date.today()
        
        is_holiday = self.is_market_holiday(check_date)
        is_weekend = self.is_weekend(check_date)
        is_open = self.is_market_open(check_date)
        
        return {
            "date": check_date.isoformat(),
            "is_open": is_open,
            "is_holiday": is_holiday,
            "is_weekend": is_weekend,
            "holiday_name": self.get_holiday_name(check_date) if is_holiday else None,
            "next_trading_day": self.get_next_trading_day(check_date).isoformat() if not is_open else None,
        }


def is_market_open_today() -> bool:
    """Check if market is open today.
    
    Returns:
        True if market is open
    """
    calendar = MarketCalendar()
    return calendar.is_market_open()


def get_market_status_today() -> dict:
    """Get today's market status.
    
    Returns:
        Market status dict
    """
    calendar = MarketCalendar()
    return calendar.get_market_status()
