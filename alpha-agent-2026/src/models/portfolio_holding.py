"""Portfolio holding model with computed signals.

Implements Constitution III (Risk Management):
- Exit/Hedge/Top-up signal logic based on SMA and position analysis
- Option B: EXIT if position > 10% OR loss > 10%, else HEDGE
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, computed_field

from src.models import Signal


class PortfolioHolding(BaseModel):
    """Portfolio holding with computed health metrics.
    
    Constitution III (Risk Management):
    - Option B: EXIT if position > 10% OR loss > 10%, else HEDGE
    - Top-up signal for positive momentum + favorable sentiment
    
    Attributes:
        symbol: Stock ticker symbol
        shares: Number of shares held
        avg_cost: Average cost basis per share
        current_price: Current market price
        sma_20: 20-day simple moving average
        sentiment_score: News sentiment (-1.0 to 1.0)
        total_portfolio_value: Total portfolio value (for position % calc)
    """
    
    # Core holding data
    symbol: str = Field(..., description="Stock ticker symbol")
    shares: float = Field(..., gt=0, description="Number of shares held")
    avg_cost: float = Field(..., gt=0, description="Average cost basis per share")
    
    # Market data
    current_price: float = Field(..., gt=0, description="Current market price")
    sma_20: float = Field(..., gt=0, description="20-day simple moving average")
    
    # Sentiment (optional, from news analysis)
    sentiment_score: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="News sentiment score (-1 to 1)"
    )
    
    # Portfolio context
    total_portfolio_value: float = Field(
        ..., gt=0, description="Total portfolio value for position % calculation"
    )
    
    # Sector (optional)
    sector: Optional[str] = Field(None, description="Market sector classification")
    
    @computed_field
    @property
    def position_value(self) -> float:
        """Calculate current position value."""
        return self.shares * self.current_price
    
    @computed_field
    @property
    def cost_basis(self) -> float:
        """Calculate total cost basis."""
        return self.shares * self.avg_cost
    
    @computed_field
    @property
    def pnl(self) -> float:
        """Calculate profit/loss in dollars."""
        return self.position_value - self.cost_basis
    
    @computed_field
    @property
    def pnl_pct(self) -> float:
        """Calculate profit/loss percentage."""
        if self.cost_basis == 0:
            return 0.0
        return ((self.position_value - self.cost_basis) / self.cost_basis) * 100
    
    @computed_field
    @property
    def position_pct(self) -> float:
        """Calculate position as percentage of portfolio."""
        if self.total_portfolio_value == 0:
            return 0.0
        return (self.position_value / self.total_portfolio_value) * 100
    
    @computed_field
    @property
    def pct_vs_sma(self) -> float:
        """Calculate price vs 20-day SMA percentage."""
        if self.sma_20 == 0:
            return 0.0
        return ((self.current_price - self.sma_20) / self.sma_20) * 100
    
    @computed_field
    @property
    def signal(self) -> Signal:
        """Determine trading signal based on Constitution III Option B.
        
        Option B Logic:
        - EXIT if position > 10% of portfolio OR loss > 10%
        - HEDGE if loss < 10% but below SMA (protective)
        - TOP_UP if positive momentum + favorable sentiment
        - HOLD otherwise
        
        Returns:
            Appropriate trading signal
        """
        # EXIT conditions (Constitution III - Option B)
        if self.position_pct > 10:
            return Signal.EXIT
        
        if self.pnl_pct < -10:
            return Signal.EXIT
        
        # HEDGE condition: Below SMA with moderate loss
        if self.pnl_pct < 0 and self.current_price < self.sma_20:
            return Signal.HEDGE
        
        # TOP_UP condition: Positive momentum + favorable sentiment
        is_above_sma = self.current_price > self.sma_20
        has_positive_momentum = self.pct_vs_sma > 2  # At least 2% above SMA
        has_favorable_sentiment = self.sentiment_score is not None and self.sentiment_score > 0.3
        
        if is_above_sma and has_positive_momentum and has_favorable_sentiment:
            return Signal.TOP_UP
        
        return Signal.HOLD
    
    @computed_field
    @property
    def signal_rationale(self) -> str:
        """Generate explanation for the signal."""
        signal = self.signal
        
        if signal == Signal.EXIT:
            if self.position_pct > 10:
                return f"Position ({self.position_pct:.1f}%) exceeds 10% concentration limit"
            else:
                return f"Loss ({self.pnl_pct:.1f}%) exceeds 10% threshold"
        
        elif signal == Signal.HEDGE:
            return f"Below 20-day SMA ({self.pct_vs_sma:.1f}%) with unrealized loss"
        
        elif signal == Signal.TOP_UP:
            return f"Positive momentum ({self.pct_vs_sma:.1f}% vs SMA) with favorable sentiment"
        
        else:
            return "Healthy position within acceptable parameters"
    
    def to_alert_dict(self) -> dict:
        """Convert to dictionary for report alerts."""
        return {
            "symbol": self.symbol,
            "signal": self.signal.value,
            "pct_vs_sma": round(self.pct_vs_sma, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "position_pct": round(self.position_pct, 2),
            "current_price": self.current_price,
            "sma_20": self.sma_20,
            "rationale": self.signal_rationale,
        }


def create_portfolio_holding(
    symbol: str,
    shares: float,
    avg_cost: float,
    current_price: float,
    sma_20: float,
    total_portfolio_value: float,
    sentiment_score: Optional[float] = None,
    sector: Optional[str] = None,
) -> PortfolioHolding:
    """Factory function to create a PortfolioHolding.
    
    Args:
        symbol: Stock ticker symbol
        shares: Number of shares
        avg_cost: Average cost basis
        current_price: Current market price
        sma_20: 20-day SMA value
        total_portfolio_value: Total portfolio value
        sentiment_score: Optional sentiment score
        sector: Optional sector classification
        
    Returns:
        PortfolioHolding with computed properties
    """
    return PortfolioHolding(
        symbol=symbol,
        shares=shares,
        avg_cost=avg_cost,
        current_price=current_price,
        sma_20=sma_20,
        total_portfolio_value=total_portfolio_value,
        sentiment_score=sentiment_score,
        sector=sector,
    )
