"""Trade recommendation model with Constitution I validation.

Implements Financial Integrity principle:
- Every trade MUST specify Entry, Target, and Stop-Loss
- 2.5% trailing stop-loss with high_water_mark tracking
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from src.models import Universe, Signal


class TradeRecommendation(BaseModel):
    """Trade recommendation with Constitution I compliance.
    
    Constitution I (Financial Integrity):
    - Every trade MUST specify Entry, Target, and Stop-Loss
    - 2.5% trailing stop-loss calculation enforced
    - high_water_mark tracks maximum price since entry
    
    Attributes:
        symbol: Stock ticker symbol
        universe: ETF universe (QQQ, IBB, ITA, SPY)
        entry: Entry price point
        target: Target price point
        stop_loss: Initial stop-loss price (must be entry * 0.975)
        current_price: Current market price
        high_water_mark: Maximum price since entry (for trailing stop)
        trailing_stop: Dynamic trailing stop (high_water_mark * 0.975)
        rsi: RSI indicator value at recommendation time
        volume_ratio: Volume vs 20-day average
        confidence: Confidence score (0.0 - 1.0)
        rationale: Explanation for the recommendation
        created_at: Timestamp of recommendation
    """
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    universe: Universe = Field(..., description="ETF universe classification")
    
    # Constitution I: Required trade parameters
    entry: float = Field(..., gt=0, description="Entry price point (REQUIRED)")
    target: float = Field(..., gt=0, description="Target price point (REQUIRED)")
    stop_loss: float = Field(..., gt=0, description="Initial stop-loss price (REQUIRED, must be entry * 0.975)")
    
    # Current state
    current_price: Optional[float] = Field(None, gt=0, description="Current market price")
    
    # Trailing stop tracking (Constitution I)
    high_water_mark: float = Field(default=0, ge=0, description="Maximum price since entry")
    trailing_stop: float = Field(default=0, ge=0, description="Dynamic trailing stop")
    
    # Technical indicators
    rsi: float = Field(..., ge=0, le=100, description="RSI value (0-100)")
    volume_ratio: float = Field(default=1.0, gt=0, description="Volume vs 20-day average")
    
    # Confidence and rationale
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0.0 - 1.0)")
    rationale: str = Field(..., min_length=10, description="Explanation for recommendation")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Normalize symbol to uppercase."""
        return v.upper().strip()
    
    @model_validator(mode="after")
    def validate_constitution_i(self) -> "TradeRecommendation":
        """Validate Constitution I requirements.
        
        Financial Integrity:
        - Stop-loss MUST be entry * 0.975 (2.5% trailing stop)
        - Target MUST be greater than entry (profit potential)
        - High water mark initialized to entry if not set
        """
        # Validate 2.5% stop-loss rule
        expected_stop = self.entry * 0.975
        tolerance = 0.001  # Allow small floating point variance
        
        if abs(self.stop_loss - expected_stop) > expected_stop * tolerance:
            raise ValueError(
                f"Constitution I violation: stop_loss ({self.stop_loss:.4f}) "
                f"must be entry * 0.975 ({expected_stop:.4f})"
            )
        
        # Validate target is above entry
        if self.target <= self.entry:
            raise ValueError(
                f"Constitution I violation: target ({self.target:.2f}) "
                f"must be greater than entry ({self.entry:.2f})"
            )
        
        # Initialize high_water_mark to entry if not set
        if self.high_water_mark == 0:
            self.high_water_mark = self.entry
            self.trailing_stop = self.high_water_mark * 0.975
        
        return self
    
    def update_trailing_stop(self, current_price: float) -> None:
        """Update trailing stop based on current price.
        
        Constitution I: 2.5% trailing stop-loss with high_water_mark tracking.
        
        The trailing stop only moves UP (never down), locking in gains
        as the price increases.
        
        Args:
            current_price: Current market price
        """
        self.current_price = current_price
        
        if current_price > self.high_water_mark:
            self.high_water_mark = current_price
            self.trailing_stop = self.high_water_mark * 0.975
    
    @property
    def signal(self) -> Signal:
        """Determine current signal based on price vs trailing stop.
        
        Returns:
            EXIT if current price below trailing stop
            HOLD otherwise
        """
        if self.current_price is None:
            return Signal.HOLD
        
        if self.current_price <= self.trailing_stop:
            return Signal.EXIT
        
        return Signal.HOLD
    
    @property
    def pnl_percent(self) -> Optional[float]:
        """Calculate P&L percentage from entry.
        
        Returns:
            Percentage gain/loss or None if no current price
        """
        if self.current_price is None:
            return None
        
        return ((self.current_price - self.entry) / self.entry) * 100
    
    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio.
        
        Returns:
            Ratio of potential reward to risk
        """
        risk = self.entry - self.stop_loss
        reward = self.target - self.entry
        
        if risk == 0:
            return 0
        
        return reward / risk
    
    @property
    def is_at_target(self) -> bool:
        """Check if current price has reached target."""
        if self.current_price is None:
            return False
        return self.current_price >= self.target
    
    @property
    def is_stopped_out(self) -> bool:
        """Check if current price has hit stop loss."""
        if self.current_price is None:
            return False
        return self.current_price <= self.trailing_stop
    
    def to_dict(self) -> dict:
        """Convert to dictionary for reporting."""
        return {
            "symbol": self.symbol,
            "universe": self.universe.value,
            "entry": self.entry,
            "target": self.target,
            "stop_loss": self.stop_loss,
            "high_water_mark": self.high_water_mark,
            "trailing_stop": self.trailing_stop,
            "rsi": self.rsi,
            "volume_ratio": self.volume_ratio,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "risk_reward": self.risk_reward_ratio,
        }


def create_trade_recommendation(
    symbol: str,
    universe: Universe,
    entry: float,
    target: float,
    rsi: float,
    confidence: float,
    rationale: str,
    volume_ratio: float = 1.0,
) -> TradeRecommendation:
    """Factory function to create a trade recommendation.
    
    Automatically calculates the 2.5% stop-loss per Constitution I.
    
    Args:
        symbol: Stock ticker symbol
        universe: ETF universe classification
        entry: Entry price point
        target: Target price point
        rsi: RSI value at recommendation
        confidence: Confidence score (0-1)
        rationale: Explanation text
        volume_ratio: Volume vs average (default 1.0)
        
    Returns:
        Validated TradeRecommendation
        
    Raises:
        ValueError: If Constitution I validation fails
    """
    # Calculate 2.5% trailing stop-loss
    stop_loss = entry * 0.975
    
    return TradeRecommendation(
        symbol=symbol,
        universe=universe,
        entry=entry,
        target=target,
        stop_loss=stop_loss,
        rsi=rsi,
        volume_ratio=volume_ratio,
        confidence=confidence,
        rationale=rationale,
    )
