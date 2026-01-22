"""Catalyst event model for market-moving events.

Implements FR-014: Time bucket classification (Today/This Week/3-Month)
"""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, computed_field

from src.models import EventType, TimeBucket


def classify_time_bucket(event_date: date) -> TimeBucket:
    """Classify an event date into a time bucket.
    
    FR-014: Events organized by Today/This Week/3-Month Horizon
    
    Args:
        event_date: The date of the event
        
    Returns:
        TimeBucket classification
    """
    today = date.today()
    days_until = (event_date - today).days
    
    if days_until < 0:
        return TimeBucket.PAST
    elif days_until == 0:
        return TimeBucket.TODAY
    elif days_until <= 7:
        return TimeBucket.THIS_WEEK
    elif days_until <= 90:
        return TimeBucket.THREE_MONTH
    else:
        return TimeBucket.BEYOND


class CatalystEvent(BaseModel):
    """Market-moving catalyst event with time bucket classification.
    
    FR-014: Events organized by Today/This Week/3-Month Horizon
    
    Attributes:
        event_type: Type of event (EARNINGS, FDA, FED, etc.)
        title: Event title/description (optional for backward compat)
        description: Event description
        event_date: Date of the event
        ticker: Related stock ticker symbol (alias for symbol)
        symbol: Related stock symbol (optional)
        details: Additional event details
        impact: Expected market impact (HIGH/MEDIUM/LOW)
    """
    
    # Support both EventType enum and string for flexibility
    event_type: str = Field(..., description="Type of catalyst event")
    event_date: date = Field(..., description="Date of the event")
    
    # Support both ticker and symbol fields
    ticker: Optional[str] = Field(None, description="Related stock ticker")
    symbol: Optional[str] = Field(None, description="Related stock symbol")
    
    # Description/title fields
    title: Optional[str] = Field(None, min_length=1, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    
    details: Optional[str] = Field(None, description="Additional details")
    impact: str = Field(default="MEDIUM", description="Expected impact level")
    source: str = Field(default="Unknown", description="Event source")
    
    @computed_field
    @property
    def time_bucket(self) -> TimeBucket:
        """Classify event into time bucket (FR-014).
        
        Uses the classify_time_bucket function for consistent classification.
        """
        return classify_time_bucket(self.event_date)
    
    @computed_field
    @property
    def days_until(self) -> int:
        """Calculate days until event."""
        return (self.event_date - date.today()).days
    
    @computed_field
    @property
    def is_past(self) -> bool:
        """Check if event has passed."""
        return self.event_date < date.today()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for reporting."""
        return {
            "event_type": self.event_type.value,
            "title": self.title,
            "event_date": self.event_date.isoformat(),
            "time_bucket": self.time_bucket.value,
            "symbol": self.symbol,
            "details": self.details,
            "impact": self.impact,
            "days_until": self.days_until,
        }


def create_catalyst_event(
    event_type: EventType,
    title: str,
    event_date: date,
    symbol: Optional[str] = None,
    details: Optional[str] = None,
    impact: str = "MEDIUM",
    source: str = "Calendar",
) -> CatalystEvent:
    """Factory function to create a CatalystEvent.
    
    Args:
        event_type: Type of event
        title: Event title
        event_date: Date of event
        symbol: Related stock symbol
        details: Additional details
        impact: Expected impact level
        source: Event source
        
    Returns:
        CatalystEvent with computed time bucket
    """
    return CatalystEvent(
        event_type=event_type,
        title=title,
        event_date=event_date,
        symbol=symbol,
        details=details,
        impact=impact,
        source=source,
    )
