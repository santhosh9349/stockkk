"""Contract tests for JSON schema compliance.

Validates that model outputs match expected JSON schemas
for report delivery and integration.
"""

import pytest
import json
from datetime import datetime
from pydantic import BaseModel

from src.models import Universe, Signal, ReportStatus
from src.models.trade_recommendation import TradeRecommendation, create_trade_recommendation
from src.models.intelligence_report import IntelligenceReport


class TestTradeRecommendationSchema:
    """Contract tests for TradeRecommendation JSON schema (T038)."""
    
    def test_required_fields_present(self):
        """Test that all required fields are in JSON output."""
        rec = create_trade_recommendation(
            symbol="AAPL",
            universe=Universe.QQQ,
            entry=150.0,
            target=165.0,
            rsi=28.5,
            confidence=0.85,
            rationale="RSI oversold with volume confirmation",
        )
        
        data = rec.model_dump()
        
        # Constitution I required fields
        assert "symbol" in data
        assert "entry" in data
        assert "target" in data
        assert "stop_loss" in data
        
        # Must have non-null values
        assert data["symbol"] is not None
        assert data["entry"] is not None
        assert data["target"] is not None
        assert data["stop_loss"] is not None
    
    def test_stop_loss_formula(self):
        """Test stop_loss is exactly entry * 0.975 (2.5% trailing stop)."""
        rec = create_trade_recommendation(
            symbol="TSLA",
            universe=Universe.QQQ,
            entry=200.0,
            target=220.0,
            rsi=25.0,
            confidence=0.75,
            rationale="Technical breakout candidate",
        )
        
        expected_stop = 200.0 * 0.975  # 195.0
        assert rec.stop_loss == expected_stop
    
    def test_invalid_stop_loss_rejected(self):
        """Test that incorrect stop_loss is rejected."""
        with pytest.raises(ValueError, match="Constitution I violation"):
            TradeRecommendation(
                symbol="AAPL",
                universe=Universe.QQQ,
                entry=100.0,
                target=110.0,
                stop_loss=96.0,  # Should be 97.5 (100 * 0.975)
                rsi=30.0,
                confidence=0.8,
                rationale="This should fail validation",
            )
    
    def test_target_must_exceed_entry(self):
        """Test that target must be greater than entry."""
        with pytest.raises(ValueError, match="Constitution I violation"):
            create_trade_recommendation(
                symbol="BAD",
                universe=Universe.SPY,
                entry=100.0,
                target=90.0,  # Below entry
                rsi=25.0,
                confidence=0.7,
                rationale="Invalid trade",
            )
    
    def test_rsi_range_validation(self):
        """Test RSI must be in 0-100 range."""
        with pytest.raises(ValueError):
            TradeRecommendation(
                symbol="TEST",
                universe=Universe.QQQ,
                entry=100.0,
                target=110.0,
                stop_loss=97.5,
                rsi=150.0,  # Invalid: > 100
                confidence=0.8,
                rationale="Should fail RSI validation",
            )
    
    def test_confidence_range_validation(self):
        """Test confidence must be in 0-1 range."""
        with pytest.raises(ValueError):
            TradeRecommendation(
                symbol="TEST",
                universe=Universe.QQQ,
                entry=100.0,
                target=110.0,
                stop_loss=97.5,
                rsi=30.0,
                confidence=1.5,  # Invalid: > 1
                rationale="Should fail confidence validation",
            )
    
    def test_json_serialization(self):
        """Test model serializes to valid JSON."""
        rec = create_trade_recommendation(
            symbol="NVDA",
            universe=Universe.QQQ,
            entry=500.0,
            target=550.0,
            rsi=32.0,
            confidence=0.9,
            rationale="Strong momentum breakout",
            volume_ratio=2.5,
        )
        
        # Should serialize without errors
        json_str = rec.model_dump_json()
        
        # Should deserialize back
        data = json.loads(json_str)
        
        assert data["symbol"] == "NVDA"
        assert data["entry"] == 500.0
        assert data["stop_loss"] == 487.5  # 500 * 0.975
    
    def test_to_dict_output(self):
        """Test to_dict method for reporting."""
        rec = create_trade_recommendation(
            symbol="META",
            universe=Universe.QQQ,
            entry=300.0,
            target=330.0,
            rsi=29.0,
            confidence=0.82,
            rationale="Oversold bounce setup",
        )
        
        data = rec.to_dict()
        
        # Check all expected keys
        expected_keys = {
            "symbol", "universe", "entry", "target", "stop_loss",
            "high_water_mark", "trailing_stop", "rsi", "volume_ratio",
            "confidence", "rationale", "risk_reward"
        }
        
        assert set(data.keys()) == expected_keys
    
    def test_trailing_stop_updates(self):
        """Test trailing stop updates with price movement."""
        rec = create_trade_recommendation(
            symbol="AAPL",
            universe=Universe.QQQ,
            entry=150.0,
            target=165.0,
            rsi=28.0,
            confidence=0.85,
            rationale="Test trailing stop",
        )
        
        # Initial state
        assert rec.high_water_mark == 150.0
        assert rec.trailing_stop == 146.25  # 150 * 0.975
        
        # Price rises
        rec.update_trailing_stop(160.0)
        assert rec.high_water_mark == 160.0
        assert rec.trailing_stop == 156.0  # 160 * 0.975
        
        # Price falls (trailing stop should NOT decrease)
        rec.update_trailing_stop(155.0)
        assert rec.high_water_mark == 160.0  # Unchanged
        assert rec.trailing_stop == 156.0  # Unchanged


class TestIntelligenceReportSchema:
    """Contract tests for IntelligenceReport JSON schema."""
    
    def test_required_fields_present(self):
        """Test all required fields exist in report."""
        report = IntelligenceReport()
        data = report.model_dump()
        
        required_fields = [
            "report_id",
            "generated_at",
            "status",
            "technical_scans",
            "portfolio_alerts",
            "catalysts",
            "macro_indicators",
            "metals_advice",
            "unavailable_sections",
        ]
        
        for field in required_fields:
            assert field in data
    
    def test_status_enum_values(self):
        """Test status is valid enum value."""
        report = IntelligenceReport()
        assert report.status in [ReportStatus.COMPLETE, ReportStatus.PARTIAL, ReportStatus.MARKET_CLOSED]
    
    def test_partial_report_schema(self):
        """Test partial report has correct structure."""
        report = IntelligenceReport()
        report.mark_unavailable("technical_scans", "API error")
        
        data = report.model_dump()
        
        assert data["status"] == "PARTIAL"
        assert "technical_scans" in data["unavailable_sections"]
    
    def test_market_closed_report_schema(self):
        """Test market closed report structure."""
        report = IntelligenceReport()
        report.mark_market_closed("Independence Day")
        
        data = report.model_dump()
        
        assert data["status"] == "MARKET_CLOSED"
        assert data["market_holiday"] is True
        assert data["holiday_name"] == "Independence Day"
    
    def test_json_serialization(self):
        """Test full report serializes to valid JSON."""
        report = IntelligenceReport()
        report.technical_scans = [
            {
                "symbol": "AAPL",
                "entry": 150.0,
                "target": 165.0,
                "stop_loss": 146.25,
            }
        ]
        
        json_str = report.model_dump_json()
        data = json.loads(json_str)
        
        assert len(data["technical_scans"]) == 1
        assert data["technical_scans"][0]["symbol"] == "AAPL"


class TestSchemaCompatibility:
    """Test schema compatibility between models."""
    
    def test_trade_recommendation_in_report(self):
        """Test TradeRecommendation can be embedded in IntelligenceReport."""
        rec = create_trade_recommendation(
            symbol="TSLA",
            universe=Universe.QQQ,
            entry=250.0,
            target=275.0,
            rsi=27.0,
            confidence=0.88,
            rationale="Breakout setup",
        )
        
        report = IntelligenceReport()
        report.technical_scans = [rec.to_dict()]
        
        # Should serialize without issues
        json_str = report.model_dump_json()
        data = json.loads(json_str)
        
        assert len(data["technical_scans"]) == 1
        assert data["technical_scans"][0]["symbol"] == "TSLA"
        assert data["technical_scans"][0]["entry"] == 250.0


class TestPortfolioHoldingSchema:
    """Contract tests for PortfolioHolding JSON schema (T049)."""
    
    def test_required_fields_present(self):
        """Test all required fields are in JSON output."""
        from src.models.portfolio_holding import PortfolioHolding
        
        holding = PortfolioHolding(
            ticker="AAPL",
            shares=100,
            avg_cost=150.0,
            current_price=165.0,
            sma_20=160.0,
            position_pct=5.0,
        )
        
        data = holding.model_dump()
        
        # Required fields
        assert "ticker" in data
        assert "shares" in data
        assert "avg_cost" in data
        assert "current_price" in data
        assert "sma_20" in data
        assert "pct_vs_sma" in data
        assert "pnl_pct" in data
        assert "signal" in data
    
    def test_computed_fields_calculated(self):
        """Test computed fields are correctly calculated."""
        from src.models.portfolio_holding import PortfolioHolding
        
        holding = PortfolioHolding(
            ticker="GOOGL",
            shares=50,
            avg_cost=100.0,
            current_price=110.0,
            sma_20=105.0,
            position_pct=8.0,
        )
        
        # pnl_pct = (current - cost) / cost * 100 = 10%
        assert holding.pnl_pct == pytest.approx(10.0, rel=0.01)
        
        # pct_vs_sma = (current - sma) / sma * 100 = 4.76%
        assert holding.pct_vs_sma == pytest.approx(4.76, rel=0.1)
    
    def test_option_b_exit_signal(self):
        """Test Option B logic: EXIT if position > 10% OR loss > 10%."""
        from src.models.portfolio_holding import PortfolioHolding
        
        # Large position (>10%) should trigger EXIT
        holding = PortfolioHolding(
            ticker="MSFT",
            shares=200,
            avg_cost=350.0,
            current_price=340.0,  # -2.86% loss
            sma_20=360.0,  # Below SMA
            position_pct=12.0,  # > 10%
        )
        
        assert holding.signal == Signal.EXIT
    
    def test_json_serialization(self):
        """Test PortfolioHolding serializes to valid JSON."""
        from src.models.portfolio_holding import PortfolioHolding
        
        holding = PortfolioHolding(
            ticker="NVDA",
            shares=25,
            avg_cost=500.0,
            current_price=550.0,
            sma_20=525.0,
            position_pct=6.0,
        )
        
        json_str = holding.model_dump_json()
        data = json.loads(json_str)
        
        assert data["ticker"] == "NVDA"
        assert data["shares"] == 25


class TestMetalsAdviceSchema:
    """Contract tests for MetalsAdvice JSON schema (T070)."""
    
    def test_constitution_iv_required_fields(self):
        """Test Constitution IV: DXY and Treasury fields required."""
        from src.models.metals_advice import MetalsAdvice, create_metals_advice
        from src.models import MetalsAction, Trend
        
        advice = create_metals_advice(
            gld_action=MetalsAction.ACCUMULATE,
            slv_action=MetalsAction.HOLD,
            gld_price=195.0,
            slv_price=22.5,
            gld_rsi=45.0,
            slv_rsi=42.0,
            dxy_value=105.0,
            dxy_trend=Trend.STRENGTHENING,
            treasury_10y=4.35,
            treasury_trend=Trend.STRENGTHENING,
            rationale="Strong dollar provides accumulation opportunity",
        )
        
        data = advice.model_dump()
        
        # Constitution IV required fields
        assert "dxy_value" in data
        assert "dxy_trend" in data
        assert "treasury_10y" in data
        assert "treasury_trend" in data
        
        # Values must be present
        assert data["dxy_value"] is not None
        assert data["dxy_trend"] is not None
        assert data["treasury_10y"] is not None
        assert data["treasury_trend"] is not None
    
    def test_metals_action_enum_values(self):
        """Test metals actions are valid enum values."""
        from src.models.metals_advice import MetalsAdvice
        from src.models import MetalsAction, Trend
        
        advice = MetalsAdvice(
            gld_action=MetalsAction.ACCUMULATE,
            slv_action=MetalsAction.PROFIT_TAKE,
            gld_price=195.0,
            slv_price=22.5,
            gld_rsi=45.0,
            slv_rsi=72.0,
            dxy_value=105.0,
            dxy_trend=Trend.STRENGTHENING,
            treasury_10y=4.35,
            treasury_trend=Trend.STRENGTHENING,
            rationale="Test actions",
        )
        
        assert advice.gld_action in [MetalsAction.ACCUMULATE, MetalsAction.HOLD, MetalsAction.PROFIT_TAKE]
        assert advice.slv_action in [MetalsAction.ACCUMULATE, MetalsAction.HOLD, MetalsAction.PROFIT_TAKE]
    
    def test_json_serialization(self):
        """Test MetalsAdvice serializes to valid JSON."""
        from src.models.metals_advice import create_metals_advice
        from src.models import MetalsAction, Trend
        
        advice = create_metals_advice(
            gld_action=MetalsAction.HOLD,
            slv_action=MetalsAction.HOLD,
            gld_price=192.0,
            slv_price=21.8,
            gld_rsi=55.0,
            slv_rsi=52.0,
            dxy_value=102.0,
            dxy_trend=Trend.STABLE,
            treasury_10y=4.20,
            treasury_trend=Trend.STABLE,
            rationale="Neutral market conditions",
        )
        
        json_str = advice.model_dump_json()
        data = json.loads(json_str)
        
        assert data["gld_action"] == "HOLD"
        assert data["dxy_value"] == 102.0
        assert data["treasury_10y"] == 4.20
