"""Metals advice model for Gold/Silver timing.

Implements Constitution IV (Macro Correlation):
- Metals weighted against DXY and Treasury yields
- Accumulate on DXY strength, profit-take on overbought + geopolitical tension
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from src.models import MetalsAction, Trend


class MetalsAdvice(BaseModel):
    """Metals timing advice per Constitution IV.
    
    Constitution IV (Macro Correlation):
    - Metals (GLD/SLV) weighted against DXY and Treasury yields
    - DXY strength → Accumulate opportunity
    - Overbought + geopolitical tension → Profit-take
    
    Required fields (Constitution IV compliance):
    - dxy_value: Current DXY value
    - dxy_trend: DXY trend direction
    - treasury_10y: 10Y Treasury yield
    - treasury_trend: Treasury trend direction
    
    Attributes:
        gld_action: Recommended action for GLD
        slv_action: Recommended action for SLV
        dxy_value: Current Dollar Index value
        dxy_trend: Dollar trend direction
        treasury_10y: 10Y Treasury yield
        treasury_trend: Treasury yield trend
        rationale: Explanation of recommendation
        geopolitical_risk: Geopolitical risk level (0-1)
        overbought_signal: Whether metals are overbought
    """
    
    # Required Constitution IV fields
    dxy_value: float = Field(..., gt=0, description="Current DXY value (REQUIRED)")
    dxy_trend: Trend = Field(..., description="DXY trend direction (REQUIRED)")
    treasury_10y: float = Field(..., description="10Y Treasury yield (REQUIRED)")
    treasury_trend: Trend = Field(..., description="Treasury trend (REQUIRED)")
    
    # Recommendations
    gld_action: MetalsAction = Field(..., description="Gold (GLD) recommendation")
    slv_action: MetalsAction = Field(..., description="Silver (SLV) recommendation")
    
    # Context
    rationale: str = Field(..., min_length=10, description="Recommendation explanation")
    geopolitical_risk: float = Field(default=0.5, ge=0, le=1, description="Geopolitical risk score")
    overbought_signal: bool = Field(default=False, description="Whether metals are overbought")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for reporting."""
        return {
            "gld_action": self.gld_action.value,
            "slv_action": self.slv_action.value,
            "dxy_value": self.dxy_value,
            "dxy_trend": self.dxy_trend.value,
            "treasury_10y": self.treasury_10y,
            "treasury_trend": self.treasury_trend.value,
            "rationale": self.rationale,
            "geopolitical_risk": self.geopolitical_risk,
            "overbought_signal": self.overbought_signal,
        }


def create_metals_advice(
    dxy_value: float,
    dxy_trend: Trend,
    treasury_10y: float,
    treasury_trend: Trend,
    gld_action: MetalsAction,
    slv_action: MetalsAction,
    rationale: str,
    geopolitical_risk: float = 0.5,
    overbought_signal: bool = False,
) -> MetalsAdvice:
    """Factory function to create MetalsAdvice.
    
    Constitution IV: All macro context fields required.
    
    Args:
        dxy_value: Current DXY value
        dxy_trend: DXY trend direction
        treasury_10y: 10Y Treasury yield
        treasury_trend: Treasury trend direction
        gld_action: Gold recommendation
        slv_action: Silver recommendation
        rationale: Explanation text
        geopolitical_risk: Risk score (0-1)
        overbought_signal: Whether metals overbought
        
    Returns:
        MetalsAdvice with all Constitution IV fields
    """
    return MetalsAdvice(
        dxy_value=dxy_value,
        dxy_trend=dxy_trend,
        treasury_10y=treasury_10y,
        treasury_trend=treasury_trend,
        gld_action=gld_action,
        slv_action=slv_action,
        rationale=rationale,
        geopolitical_risk=geopolitical_risk,
        overbought_signal=overbought_signal,
    )
