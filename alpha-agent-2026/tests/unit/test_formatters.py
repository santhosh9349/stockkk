"""Unit tests for Markdown report formatter.

Tests report formatting for GitHub Issues (FR-024).
"""

import pytest
from datetime import datetime

from src.models.intelligence_report import IntelligenceReport
from src.models import ReportStatus
from src.utils.formatters import MarkdownFormatter


class TestMarkdownFormatter:
    """Test MarkdownFormatter class."""
    
    @pytest.fixture
    def complete_report(self) -> IntelligenceReport:
        """Create a complete report for testing."""
        report = IntelligenceReport()
        report.technical_scans = [
            {
                "symbol": "TSLA",
                "universe": "QQQ",
                "entry": 250.00,
                "target": 275.00,
                "stop_loss": 243.75,
                "rsi": 32.5,
                "confidence": 0.85,
            }
        ]
        report.portfolio_alerts = [
            {
                "symbol": "AAPL",
                "signal": "HOLD",
                "pct_vs_sma": 2.5,
                "pnl_pct": 15.0,
                "rationale": "Healthy position above 20-day SMA",
            }
        ]
        report.catalysts = [
            {
                "event_type": "EARNINGS",
                "description": "AAPL Q1 Earnings",
                "time_bucket": "THIS_WEEK",
            }
        ]
        report.macro_indicators = [
            {"name": "DXY", "value": 104.25, "trend": "STRENGTHENING"},
            {"name": "10Y Treasury", "value": 4.35, "trend": "NEUTRAL"},
        ]
        report.metals_advice = {
            "gld_action": "ACCUMULATE",
            "slv_action": "HOLD",
            "dxy_value": 104.25,
            "dxy_trend": "STRENGTHENING",
            "treasury_10y": 4.35,
            "treasury_trend": "NEUTRAL",
            "rationale": "DXY strength presents accumulation opportunity",
        }
        return report
    
    @pytest.fixture
    def partial_report(self) -> IntelligenceReport:
        """Create a partial report for testing."""
        report = IntelligenceReport()
        report.mark_unavailable("technical_scans", "API timeout")
        report.portfolio_alerts = [
            {
                "symbol": "AAPL",
                "signal": "HOLD",
                "pct_vs_sma": 2.5,
                "pnl_pct": 15.0,
                "rationale": "Healthy position",
            }
        ]
        return report
    
    @pytest.fixture
    def market_closed_report(self) -> IntelligenceReport:
        """Create a market closed report for testing."""
        report = IntelligenceReport()
        report.mark_market_closed("New Year's Day")
        return report
    
    def test_format_complete_report(self, complete_report):
        """Test formatting a complete report."""
        formatter = MarkdownFormatter(complete_report)
        markdown = formatter.format()
        
        # Check header
        assert "Alpha-Agent Daily Intelligence Report" in markdown
        assert "✅ COMPLETE" in markdown
        
        # Check sections exist
        assert "## 📈 Technical Breakouts" in markdown
        assert "## 💼 Portfolio Health" in markdown
        assert "## 📅 Catalyst Calendar" in markdown
        assert "## 📊 Macro Dashboard" in markdown
        assert "## 🥇 Metals Advisor" in markdown
        
        # Check data is included
        assert "TSLA" in markdown
        assert "$250.00" in markdown
        assert "AAPL" in markdown
        assert "DXY" in markdown
        assert "ACCUMULATE" in markdown
    
    def test_format_partial_report(self, partial_report):
        """Test formatting a partial report with unavailable sections."""
        formatter = MarkdownFormatter(partial_report)
        markdown = formatter.format()
        
        # Check header shows partial status
        assert "⚠️ PARTIAL" in markdown
        
        # Check unavailable notice
        assert "Data Availability Notice" in markdown
        assert "technical_scans" in markdown
        
        # Check available section is still formatted
        assert "AAPL" in markdown
    
    def test_format_market_closed_report(self, market_closed_report):
        """Test formatting a market closed report (FR-027)."""
        formatter = MarkdownFormatter(market_closed_report)
        markdown = formatter.format()
        
        # Check market closed notice
        assert "Market Closed" in markdown
        assert "New Year's Day" in markdown
        assert "Market Holiday Notice" in markdown
        
        # Should not have regular sections
        assert "Technical Breakouts" not in markdown
    
    def test_format_summary_under_280_chars(self, complete_report):
        """Test summary is ≤280 characters (FR-025)."""
        formatter = MarkdownFormatter(complete_report)
        summary = formatter.format_summary(max_length=280)
        
        assert len(summary) <= 280
        assert "Alpha-Agent" in summary
    
    def test_format_summary_market_closed(self, market_closed_report):
        """Test summary for market closed."""
        formatter = MarkdownFormatter(market_closed_report)
        summary = formatter.format_summary()
        
        assert "Market Closed" in summary
        assert "New Year's Day" in summary
    
    def test_technical_scans_table_format(self, complete_report):
        """Test technical scans are formatted as a table."""
        formatter = MarkdownFormatter(complete_report)
        markdown = formatter.format()
        
        # Check table headers
        assert "| Symbol | Universe | Entry | Target | Stop-Loss | RSI | Confidence |" in markdown
        # Check data row
        assert "| TSLA" in markdown
    
    def test_portfolio_alerts_signal_emojis(self, complete_report):
        """Test portfolio alerts include signal emojis."""
        formatter = MarkdownFormatter(complete_report)
        markdown = formatter.format()
        
        # HOLD signal should have white circle emoji
        assert "⚪" in markdown or "HOLD" in markdown
    
    def test_catalyst_time_bucket_grouping(self, complete_report):
        """Test catalysts are grouped by time bucket."""
        formatter = MarkdownFormatter(complete_report)
        markdown = formatter.format()
        
        # Should have time bucket headers
        assert "This Week" in markdown
    
    def test_macro_dashboard_trend_indicators(self, complete_report):
        """Test macro dashboard includes trend emojis."""
        formatter = MarkdownFormatter(complete_report)
        markdown = formatter.format()
        
        # STRENGTHENING should have up arrow
        assert "📈" in markdown
    
    def test_empty_sections_handled(self):
        """Test empty sections are handled gracefully."""
        report = IntelligenceReport()
        formatter = MarkdownFormatter(report)
        markdown = formatter.format()
        
        # Should not crash, should show empty messages
        assert "No breakout candidates" in markdown or "Technical Breakouts" in markdown
    
    def test_footer_included(self, complete_report):
        """Test report includes footer."""
        formatter = MarkdownFormatter(complete_report)
        markdown = formatter.format()
        
        assert "Alpha-Agent 2026" in markdown
        assert "Automated Investment Intelligence" in markdown
