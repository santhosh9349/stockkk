"""Macro indicator model with trend calculation.

Implements macro dashboard for DXY, Treasury, CPI/PCE tracking.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, computed_field

from src.models import Trend


class MacroIndicator(BaseModel):
    """Macro economic indicator with trend analysis.
    
    Tracks key indicators for investment decisions:
    - DXY (Dollar Index) - Constitution IV correlation
    - 10Y Treasury Yield - Constitution IV context
    - CPI/PCE - Inflation indicators
    - Fed Funds Rate - Policy indicator
    
    Attributes:
        name: Indicator name (DXY, TREASURY_10Y, etc.)
        value: Current value
        previous_value: Previous value for trend calculation
        unit: Value unit (%, index, etc.)
        last_updated: Timestamp of last update
    """
    
    name: str = Field(..., description="Indicator name")
    value: float = Field(..., description="Current value")
    previous_value: Optional[float] = Field(None, description="Previous value")
    unit: str = Field(default="", description="Value unit")
    last_updated: datetime = Field(default_factory=datetime.now)
    source: str = Field(default="FRED", description="Data source")
    
    @computed_field
    @property
    def trend(self) -> Trend:
        """Calculate trend direction.
        
        Returns:
            STRENGTHENING if value increased
            WEAKENING if value decreased
            NEUTRAL if unchanged or no previous value
        """
        if self.previous_value is None:
            return Trend.NEUTRAL
        
        change = self.value - self.previous_value
        threshold = abs(self.previous_value) * 0.01  # 1% change threshold
        
        if change > threshold:
            return Trend.STRENGTHENING
        elif change < -threshold:
            return Trend.WEAKENING
        else:
            return Trend.NEUTRAL
    
    @computed_field
    @property
    def change_pct(self) -> Optional[float]:
        """Calculate percentage change from previous value."""
        if self.previous_value is None or self.previous_value == 0:
            return None
        return ((self.value - self.previous_value) / abs(self.previous_value)) * 100
    
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


def create_dxy_indicator(
    value: float, previous_value: Optional[float] = None
) -> MacroIndicator:
    """Create DXY (Dollar Index) indicator."""
    return MacroIndicator(
        name="DXY",
        value=value,
        previous_value=previous_value,
        unit="index",
        source="FRED",
    )


def create_treasury_indicator(
    value: float, previous_value: Optional[float] = None
) -> MacroIndicator:
    """Create 10Y Treasury Yield indicator."""
    return MacroIndicator(
        name="10Y Treasury",
        value=value,
        previous_value=previous_value,
        unit="%",
        source="FRED",
    )


def create_cpi_indicator(
    value: float, previous_value: Optional[float] = None
) -> MacroIndicator:
    """Create CPI (Consumer Price Index) indicator."""
    return MacroIndicator(
        name="CPI",
        value=value,
        previous_value=previous_value,
        unit="% YoY",
        source="FRED",
    )


def create_fed_funds_indicator(
    value: float, previous_value: Optional[float] = None
) -> MacroIndicator:
    """Create Fed Funds Rate indicator."""
    return MacroIndicator(
        name="Fed Funds",
        value=value,
        previous_value=previous_value,
        unit="%",
        source="FRED",
    )
