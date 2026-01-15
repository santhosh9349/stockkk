"""Catalyst event model for market-moving events.

Implements FR-014: Time bucket classification (Today/This Week/3-Month)
"""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, computed_field

from src.models import EventType, TimeBucket


class CatalystEvent(BaseModel):
    """Market-moving catalyst event with time bucket classification.
    
    FR-014: Events organized by Today/This Week/3-Month Horizon
    
    Attributes:
        event_type: Type of event (EARNINGS, FDA, FED, etc.)
        title: Event title/description
        event_date: Date of the event
        symbol: Related stock symbol (optional)
        details: Additional event details
        impact: Expected market impact (HIGH/MEDIUM/LOW)
    """
    
    event_type: EventType = Field(..., description="Type of catalyst event")
    title: str = Field(..., min_length=5, description="Event title")
    event_date: date = Field(..., description="Date of the event")
    symbol: Optional[str] = Field(None, description="Related stock symbol")
    details: Optional[str] = Field(None, description="Additional details")
    impact: str = Field(default="MEDIUM", description="Expected impact level")
    source: str = Field(default="Unknown", description="Event source")
    
    @computed_field
    @property
    def time_bucket(self) -> TimeBucket:
        """Classify event into time bucket (FR-014).
        
        Returns:
            TODAY if event is today
            THIS_WEEK if event is within 7 days
            THREE_MONTH if event is within 90 days
        """
        today = date.today()
        days_until = (self.event_date - today).days
        
        if days_until <= 0:  # Today or past
            return TimeBucket.TODAY
        elif days_until <= 7:
            return TimeBucket.THIS_WEEK
        else:
            return TimeBucket.THREE_MONTH
    
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
