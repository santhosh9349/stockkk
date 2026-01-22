"""Macro indicator model with trend calculation.

Implements macro dashboard for DXY, Treasury, CPI/PCE tracking.
"""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, computed_field

from src.models import Trend

def calculate_trend(
    current: float,
    previous: float,
    threshold: float = 0.005  # 0.5% default threshold
) -> Trend:
    """Calculate trend direction from current and previous values.
    
    Args:
        current: Current value
        previous: Previous value
        threshold: Percentage threshold for change (default 0.5%)
        
    Returns:
        STRENGTHENING if value increased beyond threshold
        WEAKENING if value decreased beyond threshold  
        STABLE if change within threshold
    """
    if previous == 0:
        # Handle zero previous value - positive current is strengthening
        if current > 0:
            return Trend.STRENGTHENING
        return Trend.STABLE
    
    change_pct = (current - previous) / abs(previous)
    
    if change_pct > threshold:
        return Trend.STRENGTHENING
    elif change_pct < -threshold:
        return Trend.WEAKENING
    else:
        return Trend.STABLE

class MacroIndicator(BaseModel):
    """Macro economic indicator with trend analysis.
    
    Tracks key indicators for investment decisions:
    - DXY (Dollar Index) - Constitution IV correlation
    - 10Y Treasury Yield - Constitution IV context
    - CPI/PCE - Inflation indicators
    - Fed Funds Rate - Policy indicator
    
    Attributes:
        name: Indicator name (DXY, TREASURY_10Y, etc.)
        value: Current value (alias: current_value)
        previous_value: Previous value for trend calculation
        unit: Value unit (%, index, etc.)
        last_updated: Timestamp of last update
        as_of_date: Date of the data (optional)
        trend: Trend direction (can be computed or explicitly set)
    """
    
    name: str = Field(..., description="Indicator name")
    
    # Support both 'value' and 'current_value' fields
    current_value: Optional[float] = Field(None, description="Current value (alias)")
    value: Optional[float] = Field(None, description="Current value")
    
    previous_value: Optional[float] = Field(None, description="Previous value")
    unit: str = Field(default="", description="Value unit")
    last_updated: datetime = Field(default_factory=datetime.now)
    source: str = Field(default="FRED", description="Data source")
    as_of_date: Optional[date] = Field(None, description="Date of the data")
    
    # Allow explicit trend setting (for tests) or compute it
    _explicit_trend: Optional[Trend] = None
    
    def __init__(self, **data):
        # Handle current_value -> value mapping
        if 'current_value' in data and data['current_value'] is not None:
            if 'value' not in data or data.get('value') is None:
                data['value'] = data['current_value']
        elif 'value' in data and data['value'] is not None:
            if 'current_value' not in data or data.get('current_value') is None:
                data['current_value'] = data['value']
        
        # Store explicit trend if provided
        explicit_trend = data.pop('trend', None)
        super().__init__(**data)
        if explicit_trend is not None:
            self._explicit_trend = explicit_trend
    
    @computed_field
    @property
    def trend(self) -> Trend:
        """Calculate trend direction.
        
        Returns:
            STRENGTHENING if value increased
            WEAKENING if value decreased
            STABLE if within threshold
            NEUTRAL if unchanged or no previous value
        """
        # Return explicit trend if set
        if self._explicit_trend is not None:
            return self._explicit_trend
            
        if self.previous_value is None:
            return Trend.NEUTRAL
        
        current = self.value if self.value is not None else self.current_value
        if current is None:
            return Trend.NEUTRAL
            
        return calculate_trend(current, self.previous_value, threshold=0.005)
    
    @computed_field
    @property
    def change_pct(self) -> Optional[float]:
        """Calculate percentage change from previous value."""
        current = self.value if self.value is not None else self.current_value
        if self.previous_value is None or self.previous_value == 0 or current is None:
            return None
        return ((current - self.previous_value) / abs(self.previous_value)) * 100
    
    @property
    def trend_emoji(self) -> str:
        """Get emoji representation of trend."""
        if self.trend == Trend.STRENGTHENING:
            return "📈"
        elif self.trend == Trend.WEAKENING:
            return "📉"
        else:
            return "➡️"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for reporting."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "trend": self.trend.value,
            "change_pct": self.change_pct,
            "last_updated": self.last_updated.isoformat(),
        }
    
    def display_string(self) -> str:
        """Get formatted display string for the indicator."""
        current = self.value if self.value is not None else self.current_value
        trend_str = self.trend.value.lower()
        return f"{self.name}: {current:.2f}{self.unit} ({trend_str})"


def create_dxy_indicator(
    value: Optional[float] = None,
    previous_value: Optional[float] = None,
    current: Optional[float] = None,
    previous: Optional[float] = None,
) -> MacroIndicator:
    """Create DXY (Dollar Index) indicator.
    
    Supports both old (value/previous_value) and new (current/previous) arg styles.
    """
    actual_value = value if value is not None else current
    actual_previous = previous_value if previous_value is not None else previous
    return MacroIndicator(
        name="DXY",
        value=actual_value,
        previous_value=actual_previous,
        unit="index",
        source="FRED",
    )


def create_treasury_indicator(
    value: Optional[float] = None,
    previous_value: Optional[float] = None,
    current: Optional[float] = None,
    previous: Optional[float] = None,
) -> MacroIndicator:
    """Create 10Y Treasury Yield indicator.
    
    Supports both old (value/previous_value) and new (current/previous) arg styles.
    """
    actual_value = value if value is not None else current
    actual_previous = previous_value if previous_value is not None else previous
    return MacroIndicator(
        name="Treasury 10Y",
        value=actual_value,
        previous_value=actual_previous,
        unit="%",
        source="FRED",
    )


def create_cpi_indicator(
    value: Optional[float] = None,
    previous_value: Optional[float] = None,
    current: Optional[float] = None,
    previous: Optional[float] = None,
) -> MacroIndicator:
    """Create CPI (Consumer Price Index) indicator.
    
    Supports both old (value/previous_value) and new (current/previous) arg styles.
    """
    actual_value = value if value is not None else current
    actual_previous = previous_value if previous_value is not None else previous
    return MacroIndicator(
        name="CPI",
        value=actual_value,
        previous_value=actual_previous,
        unit="% YoY",
        source="FRED",
    )


def create_fed_funds_indicator(
    value: Optional[float] = None,
    previous_value: Optional[float] = None,
    current: Optional[float] = None,
    previous: Optional[float] = None,
) -> MacroIndicator:
    """Create Fed Funds Rate indicator.
    
    Supports both old (value/previous_value) and new (current/previous) arg styles.
    """
    actual_value = value if value is not None else current
    actual_previous = previous_value if previous_value is not None else previous
    return MacroIndicator(
        name="Fed Funds",
        value=actual_value,
        previous_value=actual_previous,
        unit="%",
        source="FRED",
    )
