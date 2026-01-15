"""End-to-end test for Alpha-Agent pipeline."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from src.agents.orchestrator import AlphaAgentOrchestrator
from src.models import ReportStatus
from src.utils.config import Config


@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    config = MagicMock(spec=Config)
    config.alpha_vantage_api_key = "test_av_key"
    config.fred_api_key = "test_fred_key"
    config.finnhub_api_key = "test_finnhub_key"
    config.portfolio_path = "data/portfolio.example.json"
    config.universe_symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "NVDA"]
    return config


class TestEndToEndPipeline:
    """End-to-end tests for the full Alpha-Agent pipeline."""
    
    @pytest.mark.asyncio
    async def test_dry_run_pipeline_completes(self, mock_config):
        """Test that dry run pipeline completes without errors."""
        orchestrator = AlphaAgentOrchestrator(
            config=mock_config,
            dry_run=True,
        )
        
        report = await orchestrator.run()
        
        # Should complete without raising
        assert report is not None
        assert report.status in [ReportStatus.COMPLETE, ReportStatus.PARTIAL]
    
    @pytest.mark.asyncio
    async def test_market_closed_mode(self, mock_config):
        """Test market closed mode returns appropriate response."""
        orchestrator = AlphaAgentOrchestrator(
            config=mock_config,
            dry_run=True,
        )
        
        report = await orchestrator.run(market_closed=True)
        
        assert report is not None
        # Market closed should skip all agents
    
    @pytest.mark.asyncio
    async def test_partial_report_on_agent_failure(self, mock_config):
        """Test that pipeline continues and creates partial report when agent fails."""
        orchestrator = AlphaAgentOrchestrator(
            config=mock_config,
            dry_run=True,
        )
        
        # Force technical scanner to fail
        orchestrator._technical_scanner.scan = AsyncMock(
            side_effect=Exception("Simulated scanner failure")
        )
        
        report = await orchestrator.run()
        
        # Should still have report (partial)
        assert report is not None
        # Technical scans should be marked unavailable
        assert "technical_scans" in report.unavailable_sections or \
               len(report.technical_scans) == 0


class TestConstitutionCompliance:
    """Test Constitution principle compliance in pipeline."""
    
    @pytest.mark.asyncio
    async def test_constitution_i_stop_loss(self, mock_config):
        """Test Constitution I: All recommendations have 2.5% stop-loss."""
        orchestrator = AlphaAgentOrchestrator(
            config=mock_config,
            dry_run=True,
        )
        
        report = await orchestrator.run()
        
        # Check technical scans for stop-loss
        for scan in report.technical_scans:
            if "entry" in scan and "stop_loss" in scan:
                entry = scan["entry"]
                stop_loss = scan["stop_loss"]
                expected_stop = entry * 0.975  # 2.5% below entry
                assert stop_loss == pytest.approx(expected_stop, rel=0.01), \
                    f"Stop loss {stop_loss} not 2.5% below entry {entry}"
    
    @pytest.mark.asyncio
    async def test_constitution_iv_metals_has_dxy(self, mock_config):
        """Test Constitution IV: Metals advice includes DXY correlation."""
        orchestrator = AlphaAgentOrchestrator(
            config=mock_config,
            dry_run=True,
        )
        
        report = await orchestrator.run()
        
        if report.metals_advice:
            # Constitution IV requires DXY data
            assert "dxy_value" in report.metals_advice
            assert "dxy_trend" in report.metals_advice
            assert "treasury_10y" in report.metals_advice
            assert "treasury_trend" in report.metals_advice


class TestReportStructure:
    """Test report structure and completeness."""
    
    @pytest.mark.asyncio
    async def test_report_has_all_sections(self, mock_config):
        """Test that complete report has all expected sections."""
        orchestrator = AlphaAgentOrchestrator(
            config=mock_config,
            dry_run=True,
        )
        
        report = await orchestrator.run()
        
        # Check for all expected sections
        assert hasattr(report, "technical_scans")
        assert hasattr(report, "portfolio_alerts")
        assert hasattr(report, "catalysts")
        assert hasattr(report, "macro_indicators")
        assert hasattr(report, "metals_advice")
    
    @pytest.mark.asyncio
    async def test_report_serialization(self, mock_config):
        """Test that report can be serialized to JSON."""
        orchestrator = AlphaAgentOrchestrator(
            config=mock_config,
            dry_run=True,
        )
        
        report = await orchestrator.run()
        
        # Should be able to convert to dict
        report_dict = report.model_dump() if hasattr(report, 'model_dump') else report.__dict__
        
        assert isinstance(report_dict, dict)
