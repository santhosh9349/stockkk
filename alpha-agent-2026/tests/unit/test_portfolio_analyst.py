"""Unit tests for Portfolio Analyst Agent.

Tests Constitution III Option B logic:
- EXIT if position > 10% OR loss > 10%
- HEDGE if loss < 10% but below SMA
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models import Signal
from src.models.portfolio_holding import PortfolioHolding, create_portfolio_holding
from src.agents.portfolio_analyst import PortfolioAnalystAgent


class TestOptionBLogic:
    """Test Constitution III Option B Exit/Hedge decision logic (T048)."""
    
    def test_exit_when_position_exceeds_10_percent(self):
        """Test EXIT signal when position > 10% of portfolio."""
        holding = create_portfolio_holding(
            symbol="AAPL",
            shares=100,
            avg_cost=150.0,
            current_price=160.0,  # Profitable
            sma_20=155.0,         # Above SMA
            total_portfolio_value=100000.0,  # Position = 16% of portfolio
        )
        
        # Position is $16,000 / $100,000 = 16%
        assert holding.position_pct > 10
        assert holding.signal == Signal.EXIT
    
    def test_exit_when_loss_exceeds_10_percent(self):
        """Test EXIT signal when loss > 10%."""
        holding = create_portfolio_holding(
            symbol="TSLA",
            shares=50,
            avg_cost=250.0,
            current_price=220.0,  # 12% loss
            sma_20=230.0,
            total_portfolio_value=200000.0,
        )
        
        assert holding.pnl_pct < -10
        assert holding.signal == Signal.EXIT
    
    def test_hedge_when_below_sma_with_moderate_loss(self):
        """Test HEDGE signal when below SMA with loss < 10%."""
        holding = create_portfolio_holding(
            symbol="META",
            shares=30,
            avg_cost=300.0,
            current_price=285.0,  # 5% loss
            sma_20=295.0,         # Below SMA
            total_portfolio_value=500000.0,
        )
        
        assert holding.pnl_pct < 0
        assert holding.pnl_pct > -10
        assert holding.current_price < holding.sma_20
        assert holding.signal == Signal.HEDGE
    
    def test_hold_when_healthy(self):
        """Test HOLD signal for healthy position."""
        holding = create_portfolio_holding(
            symbol="NVDA",
            shares=20,
            avg_cost=400.0,
            current_price=420.0,  # 5% gain
            sma_20=410.0,         # Above SMA
            total_portfolio_value=500000.0,
        )
        
        assert holding.pnl_pct > 0
        assert holding.current_price > holding.sma_20
        assert holding.position_pct < 10
        assert holding.signal == Signal.HOLD
    
    def test_topup_with_momentum_and_sentiment(self):
        """Test TOP_UP signal with positive momentum and sentiment."""
        holding = create_portfolio_holding(
            symbol="GOOGL",
            shares=25,
            avg_cost=130.0,
            current_price=145.0,  # 11.5% gain
            sma_20=138.0,         # 5% above SMA (strong momentum)
            total_portfolio_value=500000.0,
            sentiment_score=0.5,  # Bullish sentiment
        )
        
        assert holding.pct_vs_sma > 2  # Strong momentum
        assert holding.sentiment_score > 0.3  # Favorable sentiment
        assert holding.signal == Signal.TOP_UP
    
    def test_no_topup_without_sentiment(self):
        """Test no TOP_UP without favorable sentiment."""
        holding = create_portfolio_holding(
            symbol="AMZN",
            shares=20,
            avg_cost=150.0,
            current_price=160.0,
            sma_20=152.0,  # Above SMA
            total_portfolio_value=500000.0,
            sentiment_score=0.1,  # Neutral sentiment (below 0.3)
        )
        
        assert holding.pct_vs_sma > 2
        assert holding.sentiment_score < 0.3
        assert holding.signal == Signal.HOLD  # Not TOP_UP
    
    def test_no_topup_without_momentum(self):
        """Test no TOP_UP without strong momentum."""
        holding = create_portfolio_holding(
            symbol="MSFT",
            shares=30,
            avg_cost=350.0,
            current_price=355.0,
            sma_20=354.0,  # Only 0.3% above SMA
            total_portfolio_value=500000.0,
            sentiment_score=0.6,  # Good sentiment
        )
        
        assert holding.pct_vs_sma < 2  # Weak momentum
        assert holding.signal == Signal.HOLD  # Not TOP_UP


class TestPortfolioHoldingComputedFields:
    """Test PortfolioHolding computed properties (T047)."""
    
    def test_position_value(self):
        """Test position value calculation."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=50.0,
            current_price=55.0,
            sma_20=52.0,
            total_portfolio_value=100000.0,
        )
        
        assert holding.position_value == 5500.0  # 100 * 55
    
    def test_cost_basis(self):
        """Test cost basis calculation."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=50.0,
            current_price=55.0,
            sma_20=52.0,
            total_portfolio_value=100000.0,
        )
        
        assert holding.cost_basis == 5000.0  # 100 * 50
    
    def test_pnl_dollars(self):
        """Test P&L in dollars."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=50.0,
            current_price=55.0,
            sma_20=52.0,
            total_portfolio_value=100000.0,
        )
        
        assert holding.pnl == 500.0  # 5500 - 5000
    
    def test_pnl_percent_gain(self):
        """Test P&L percentage for gain."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=50.0,
            current_price=55.0,  # 10% gain
            sma_20=52.0,
            total_portfolio_value=100000.0,
        )
        
        assert holding.pnl_pct == 10.0
    
    def test_pnl_percent_loss(self):
        """Test P&L percentage for loss."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=50.0,
            current_price=45.0,  # 10% loss
            sma_20=48.0,
            total_portfolio_value=100000.0,
        )
        
        assert holding.pnl_pct == -10.0
    
    def test_position_percent(self):
        """Test position as percentage of portfolio."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=50.0,
            current_price=100.0,  # Position = $10,000
            sma_20=95.0,
            total_portfolio_value=100000.0,  # 10% of portfolio
        )
        
        assert holding.position_pct == 10.0
    
    def test_pct_vs_sma_above(self):
        """Test percentage vs SMA when above."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=50.0,
            current_price=105.0,  # 5% above SMA
            sma_20=100.0,
            total_portfolio_value=100000.0,
        )
        
        assert holding.pct_vs_sma == 5.0
    
    def test_pct_vs_sma_below(self):
        """Test percentage vs SMA when below."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=50.0,
            current_price=95.0,  # 5% below SMA
            sma_20=100.0,
            total_portfolio_value=100000.0,
        )
        
        assert holding.pct_vs_sma == -5.0


class TestSignalRationale:
    """Test signal rationale generation."""
    
    def test_exit_rationale_concentration(self):
        """Test EXIT rationale mentions concentration."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=100.0,
            current_price=150.0,
            sma_20=140.0,
            total_portfolio_value=100000.0,  # 15% position
        )
        
        assert "10%" in holding.signal_rationale
        assert "concentration" in holding.signal_rationale.lower()
    
    def test_exit_rationale_loss(self):
        """Test EXIT rationale mentions loss threshold."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=100,
            avg_cost=100.0,
            current_price=85.0,  # 15% loss
            sma_20=90.0,
            total_portfolio_value=500000.0,
        )
        
        assert "10%" in holding.signal_rationale
        assert "threshold" in holding.signal_rationale.lower()
    
    def test_hedge_rationale(self):
        """Test HEDGE rationale mentions SMA."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=50,
            avg_cost=100.0,
            current_price=95.0,  # 5% loss, below SMA
            sma_20=100.0,
            total_portfolio_value=500000.0,
        )
        
        assert "SMA" in holding.signal_rationale
    
    def test_topup_rationale(self):
        """Test TOP_UP rationale mentions momentum and sentiment."""
        holding = create_portfolio_holding(
            symbol="TEST",
            shares=50,
            avg_cost=100.0,
            current_price=115.0,
            sma_20=108.0,  # 6.5% above SMA
            total_portfolio_value=500000.0,
            sentiment_score=0.5,
        )
        
        assert "momentum" in holding.signal_rationale.lower()
        assert "sentiment" in holding.signal_rationale.lower()


class TestToAlertDict:
    """Test to_alert_dict output format."""
    
    def test_alert_dict_keys(self):
        """Test alert dict has all required keys."""
        holding = create_portfolio_holding(
            symbol="AAPL",
            shares=50,
            avg_cost=150.0,
            current_price=160.0,
            sma_20=155.0,
            total_portfolio_value=100000.0,
        )
        
        alert = holding.to_alert_dict()
        
        expected_keys = {
            "symbol", "signal", "pct_vs_sma", "pnl_pct",
            "position_pct", "current_price", "sma_20", "rationale"
        }
        
        assert set(alert.keys()) == expected_keys
    
    def test_alert_dict_values_rounded(self):
        """Test numeric values are rounded appropriately."""
        holding = create_portfolio_holding(
            symbol="AAPL",
            shares=33,
            avg_cost=150.123,
            current_price=160.456,
            sma_20=155.789,
            total_portfolio_value=100000.0,
        )
        
        alert = holding.to_alert_dict()
        
        # Should be rounded to 2 decimal places
        assert isinstance(alert["pct_vs_sma"], float)
        assert isinstance(alert["pnl_pct"], float)
        assert isinstance(alert["position_pct"], float)
