"""Unit tests for Metals Advisor Agent.

Tests Constitution IV DXY correlation recommendation logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models import MetalsAction, Trend
from src.agents.metals_advisor import MetalsAdvisorAgent


class TestDXYCorrelationLogic:
    """Test DXY correlation recommendation logic (T069)."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.fred_api_key = None  # Use mock client
        return config
    
    @pytest.fixture
    def agent(self, mock_config):
        """Create agent instance."""
        return MetalsAdvisorAgent(mock_config)
    
    def test_strong_dxy_strengthening_accumulate(self, agent):
        """Test ACCUMULATE when DXY > 105 and strengthening."""
        action = agent._determine_gld_action(
            dxy_value=106.0,  # Strong
            dxy_trend=Trend.STRENGTHENING,
            treasury_value=4.0,
            treasury_trend=Trend.NEUTRAL,
        )
        
        assert action == MetalsAction.ACCUMULATE
    
    def test_strong_dxy_neutral_hold(self, agent):
        """Test HOLD when DXY > 105 but not strengthening."""
        action = agent._determine_gld_action(
            dxy_value=106.0,
            dxy_trend=Trend.NEUTRAL,
            treasury_value=4.0,
            treasury_trend=Trend.NEUTRAL,
        )
        
        assert action == MetalsAction.HOLD
    
    def test_weak_dxy_weakening_profit_take(self, agent):
        """Test PROFIT_TAKE when DXY < 100 and weakening."""
        action = agent._determine_gld_action(
            dxy_value=98.0,  # Weak
            dxy_trend=Trend.WEAKENING,
            treasury_value=4.0,
            treasury_trend=Trend.NEUTRAL,
        )
        
        assert action == MetalsAction.PROFIT_TAKE
    
    def test_weak_dxy_neutral_hold(self, agent):
        """Test HOLD when DXY < 100 but not weakening."""
        action = agent._determine_gld_action(
            dxy_value=98.0,
            dxy_trend=Trend.NEUTRAL,
            treasury_value=4.0,
            treasury_trend=Trend.NEUTRAL,
        )
        
        assert action == MetalsAction.HOLD
    
    def test_high_treasury_hold(self, agent):
        """Test HOLD when Treasury > 4.5%."""
        action = agent._determine_gld_action(
            dxy_value=103.0,  # Neutral DXY
            dxy_trend=Trend.NEUTRAL,
            treasury_value=4.8,  # High yield
            treasury_trend=Trend.NEUTRAL,
        )
        
        assert action == MetalsAction.HOLD
    
    def test_low_treasury_accumulate(self, agent):
        """Test ACCUMULATE when Treasury < 3.5%."""
        action = agent._determine_gld_action(
            dxy_value=103.0,  # Neutral DXY
            dxy_trend=Trend.NEUTRAL,
            treasury_value=3.2,  # Low yield
            treasury_trend=Trend.NEUTRAL,
        )
        
        assert action == MetalsAction.ACCUMULATE
    
    def test_neutral_conditions_hold(self, agent):
        """Test HOLD when all conditions neutral."""
        action = agent._determine_gld_action(
            dxy_value=103.0,
            dxy_trend=Trend.NEUTRAL,
            treasury_value=4.0,
            treasury_trend=Trend.NEUTRAL,
        )
        
        assert action == MetalsAction.HOLD


class TestSilverLogic:
    """Test silver (SLV) recommendation logic."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.fred_api_key = None
        return config
    
    @pytest.fixture
    def agent(self, mock_config):
        """Create agent instance."""
        return MetalsAdvisorAgent(mock_config)
    
    def test_silver_more_conservative(self, agent):
        """Test silver is more conservative than gold."""
        # For same conditions, silver should be same or more conservative
        gld_action = agent._determine_gld_action(
            dxy_value=106.0,
            dxy_trend=Trend.STRENGTHENING,
            treasury_value=4.0,
            treasury_trend=Trend.NEUTRAL,
        )
        
        slv_action = agent._determine_slv_action(
            dxy_value=106.0,
            dxy_trend=Trend.STRENGTHENING,
            treasury_value=4.0,
            treasury_trend=Trend.NEUTRAL,
        )
        
        # Silver should only accumulate in very strong DXY
        assert gld_action == MetalsAction.ACCUMULATE
        # Silver more conservative at DXY 106 (needs > 106 to accumulate)
        assert slv_action in [MetalsAction.ACCUMULATE, MetalsAction.HOLD]
    
    def test_silver_accumulate_very_strong_dxy(self, agent):
        """Test silver accumulates only with very strong DXY."""
        slv_action = agent._determine_slv_action(
            dxy_value=108.0,  # Very strong
            dxy_trend=Trend.STRENGTHENING,
            treasury_value=4.0,
            treasury_trend=Trend.NEUTRAL,
        )
        
        assert slv_action == MetalsAction.ACCUMULATE


class TestTrendCalculation:
    """Test trend calculation from values."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.fred_api_key = None
        return config
    
    @pytest.fixture
    def agent(self, mock_config):
        """Create agent instance."""
        return MetalsAdvisorAgent(mock_config)
    
    def test_strengthening_trend(self, agent):
        """Test strengthening trend detection."""
        trend = agent._calculate_trend(105.0, 102.0)  # > 1% increase
        assert trend == Trend.STRENGTHENING
    
    def test_weakening_trend(self, agent):
        """Test weakening trend detection."""
        trend = agent._calculate_trend(100.0, 103.0)  # > 1% decrease
        assert trend == Trend.WEAKENING
    
    def test_neutral_trend(self, agent):
        """Test neutral trend when change < 1%."""
        trend = agent._calculate_trend(103.5, 103.0)  # < 1% change
        assert trend == Trend.NEUTRAL
    
    def test_neutral_no_previous(self, agent):
        """Test neutral when no previous value."""
        trend = agent._calculate_trend(103.0, None)
        assert trend == Trend.NEUTRAL


class TestRationaleGeneration:
    """Test rationale text generation."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.fred_api_key = None
        return config
    
    @pytest.fixture
    def agent(self, mock_config):
        """Create agent instance."""
        return MetalsAdvisorAgent(mock_config)
    
    def test_rationale_mentions_dxy(self, agent):
        """Test rationale includes DXY context."""
        rationale = agent._generate_rationale(
            dxy_value=106.0,
            dxy_trend=Trend.STRENGTHENING,
            treasury_value=4.0,
            treasury_trend=Trend.NEUTRAL,
            gld_action=MetalsAction.ACCUMULATE,
            slv_action=MetalsAction.HOLD,
        )
        
        assert "DXY" in rationale
        assert "106" in rationale
    
    def test_rationale_mentions_treasury(self, agent):
        """Test rationale includes Treasury context."""
        rationale = agent._generate_rationale(
            dxy_value=103.0,
            dxy_trend=Trend.NEUTRAL,
            treasury_value=4.8,
            treasury_trend=Trend.STRENGTHENING,
            gld_action=MetalsAction.HOLD,
            slv_action=MetalsAction.HOLD,
        )
        
        assert "yield" in rationale.lower() or "4.8" in rationale


class TestMetalsAdvisorIntegration:
    """Integration tests for full metals analysis."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.fred_api_key = None
        return config
    
    @pytest.mark.asyncio
    async def test_analyze_returns_dict(self, mock_config):
        """Test analyze returns proper dict structure."""
        agent = MetalsAdvisorAgent(mock_config)
        result = await agent.analyze()
        
        # Check required fields (Constitution IV)
        assert "gld_action" in result
        assert "slv_action" in result
        assert "dxy_value" in result
        assert "dxy_trend" in result
        assert "treasury_10y" in result
        assert "treasury_trend" in result
        assert "rationale" in result
    
    @pytest.mark.asyncio
    async def test_analyze_with_macro_context(self, mock_config):
        """Test analyze uses provided macro context."""
        macro_context = {
            "dxy_value": 108.0,
            "dxy_trend": Trend.STRENGTHENING,
            "treasury_10y": 3.0,
            "treasury_trend": Trend.WEAKENING,
        }
        
        agent = MetalsAdvisorAgent(mock_config, macro_context)
        result = await agent.analyze()
        
        assert result["dxy_value"] == 108.0
        # Strong DXY + strengthening should give ACCUMULATE
        assert result["gld_action"] == "ACCUMULATE"
