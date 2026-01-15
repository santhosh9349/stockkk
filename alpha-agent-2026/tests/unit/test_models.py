"""Unit tests for Pydantic data models.

Tests Constitution compliance for all entity models.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from src.models import (
    Universe,
    Signal,
    EventType,
    TimeBucket,
    Trend,
    ReportStatus,
    MetalsAction,
)
from src.models.intelligence_report import IntelligenceReport, DataUnavailable


class TestEnumerations:
    """Test all enumeration types."""
    
    def test_universe_values(self):
        """Test Universe enum has all expected values."""
        assert Universe.QQQ.value == "QQQ"
        assert Universe.IBB.value == "IBB"
        assert Universe.ITA.value == "ITA"
        assert Universe.SPY.value == "SPY"
    
    def test_signal_values(self):
        """Test Signal enum has all expected values (Constitution III)."""
        assert Signal.EXIT.value == "EXIT"
        assert Signal.HEDGE.value == "HEDGE"
        assert Signal.TOP_UP.value == "TOP_UP"
        assert Signal.HOLD.value == "HOLD"
    
    def test_time_bucket_values(self):
        """Test TimeBucket enum has all expected values (FR-014)."""
        assert TimeBucket.TODAY.value == "TODAY"
        assert TimeBucket.THIS_WEEK.value == "THIS_WEEK"
        assert TimeBucket.THREE_MONTH.value == "THREE_MONTH"
    
    def test_report_status_values(self):
        """Test ReportStatus enum has all expected values."""
        assert ReportStatus.COMPLETE.value == "COMPLETE"
        assert ReportStatus.PARTIAL.value == "PARTIAL"
        assert ReportStatus.MARKET_CLOSED.value == "MARKET_CLOSED"
    
    def test_metals_action_values(self):
        """Test MetalsAction enum has all expected values (Constitution IV)."""
        assert MetalsAction.ACCUMULATE.value == "ACCUMULATE"
        assert MetalsAction.PROFIT_TAKE.value == "PROFIT_TAKE"
        assert MetalsAction.HOLD.value == "HOLD"


class TestDataUnavailable:
    """Test DataUnavailable sentinel class."""
    
    def test_creation(self):
        """Test DataUnavailable can be created with source and error."""
        marker = DataUnavailable(source="alpha_vantage", error="API timeout")
        
        assert marker.source == "alpha_vantage"
        assert marker.error == "API timeout"
        assert marker.timestamp is not None
    
    def test_repr(self):
        """Test DataUnavailable string representation."""
        marker = DataUnavailable(source="fred", error="Rate limit")
        
        assert "fred" in repr(marker)
        assert "Rate limit" in repr(marker)
    
    def test_to_markdown(self):
        """Test DataUnavailable Markdown formatting."""
        marker = DataUnavailable(source="bloomberg", error="Auth failed")
        md = marker.to_markdown()
        
        assert "⚠️" in md
        assert "Data Unavailable" in md
        assert "bloomberg" in md
        assert "Auth failed" in md


class TestIntelligenceReport:
    """Test IntelligenceReport model."""
    
    def test_default_creation(self):
        """Test report creates with default values."""
        report = IntelligenceReport()
        
        assert report.report_id is not None
        assert report.generated_at is not None
        assert report.status == ReportStatus.COMPLETE
        assert report.technical_scans == []
        assert report.portfolio_alerts == []
        assert report.catalysts == []
        assert report.macro_indicators == []
        assert report.metals_advice is None
        assert report.unavailable_sections == []
    
    def test_mark_unavailable(self):
        """Test marking sections as unavailable (FR-026)."""
        report = IntelligenceReport()
        
        report.mark_unavailable("technical_scans", "API error")
        
        assert "technical_scans" in report.unavailable_sections
        assert report.status == ReportStatus.PARTIAL
        assert report.is_partial is True
        assert report.is_complete is False
    
    def test_mark_unavailable_no_duplicates(self):
        """Test marking same section twice doesn't duplicate."""
        report = IntelligenceReport()
        
        report.mark_unavailable("catalysts")
        report.mark_unavailable("catalysts")
        
        assert report.unavailable_sections.count("catalysts") == 1
    
    def test_mark_market_closed(self):
        """Test marking report as market closed (FR-027)."""
        report = IntelligenceReport()
        
        report.mark_market_closed("New Year's Day")
        
        assert report.status == ReportStatus.MARKET_CLOSED
        assert report.market_holiday is True
        assert report.holiday_name == "New Year's Day"
        assert report.is_market_closed is True
    
    def test_get_summary_stats(self):
        """Test summary statistics generation."""
        report = IntelligenceReport()
        report.technical_scans = [{"symbol": "AAPL"}, {"symbol": "TSLA"}]
        report.portfolio_alerts = [{"symbol": "NVDA"}]
        report.catalysts = [{"event": "Earnings"}]
        report.macro_indicators = [{"name": "DXY"}, {"name": "CPI"}]
        report.metals_advice = {"gld_action": "HOLD"}
        
        stats = report.get_summary_stats()
        
        assert stats["technical_scans"] == 2
        assert stats["portfolio_alerts"] == 1
        assert stats["catalysts"] == 1
        assert stats["macro_indicators"] == 2
        assert stats["has_metals_advice"] == 1
        assert stats["unavailable_sections"] == 0
    
    def test_is_complete_property(self):
        """Test is_complete property."""
        report = IntelligenceReport()
        assert report.is_complete is True
        
        report.mark_unavailable("test")
        assert report.is_complete is False
    
    def test_is_partial_property(self):
        """Test is_partial property."""
        report = IntelligenceReport()
        assert report.is_partial is False
        
        report.mark_unavailable("test")
        assert report.is_partial is True
