"""Integration tests for full pipeline execution.

Tests end-to-end pipeline with mocked external services.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.orchestrator import AlphaAgentOrchestrator
from src.models.intelligence_report import IntelligenceReport
from src.models import ReportStatus
from src.utils.config import Config


@pytest.fixture
def mock_config() -> Config:
    """Create mock configuration for testing."""
    return Config(
        alpha_vantage_api_key="test_av_key",
        fred_api_key="test_fred_key",
        telegram_bot_token="test_bot_token",
        telegram_chat_id="123456789",
        github_token="test_gh_token",
        github_repository="test/repo",
    )


class TestAlphaAgentOrchestrator:
    """Test AlphaAgentOrchestrator pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_returns_report(self, mock_config):
        """Test full pipeline returns IntelligenceReport."""
        orchestrator = AlphaAgentOrchestrator(mock_config)
        
        report = await orchestrator.run()
        
        assert isinstance(report, IntelligenceReport)
        assert report.report_id is not None
        assert report.generated_at is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_market_closed_mode(self, mock_config):
        """Test pipeline in market closed mode (FR-027)."""
        orchestrator = AlphaAgentOrchestrator(mock_config)
        
        report = await orchestrator.run(market_closed=True)
        
        assert report.status == ReportStatus.MARKET_CLOSED
        assert report.is_market_closed is True
        # Agents should not have run
        assert report.technical_scans == [] or len(report.technical_scans) == 0
    
    @pytest.mark.asyncio
    async def test_pipeline_populates_all_sections(self, mock_config):
        """Test pipeline populates all report sections (MVP placeholder data)."""
        orchestrator = AlphaAgentOrchestrator(mock_config)
        
        report = await orchestrator.run()
        
        # MVP uses placeholder data
        assert len(report.technical_scans) > 0
        assert len(report.portfolio_alerts) > 0
        assert len(report.catalysts) > 0
        assert len(report.macro_indicators) > 0
        assert report.metals_advice is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_status_complete_on_success(self, mock_config):
        """Test pipeline status is COMPLETE when all agents succeed."""
        orchestrator = AlphaAgentOrchestrator(mock_config)
        
        report = await orchestrator.run()
        
        # With placeholder data, should be complete
        assert report.status == ReportStatus.COMPLETE
        assert len(report.unavailable_sections) == 0


class TestPipelineIntegration:
    """Integration tests for full pipeline flow."""
    
    @pytest.mark.asyncio
    async def test_pipeline_to_markdown_flow(self, mock_config):
        """Test pipeline output can be formatted to Markdown."""
        from src.utils.formatters import MarkdownFormatter
        
        orchestrator = AlphaAgentOrchestrator(mock_config)
        report = await orchestrator.run()
        
        formatter = MarkdownFormatter(report)
        markdown = formatter.format()
        
        assert "Alpha-Agent Daily Intelligence Report" in markdown
        assert "Technical Breakouts" in markdown
        assert "Portfolio Health" in markdown
    
    @pytest.mark.asyncio
    async def test_pipeline_to_summary_flow(self, mock_config):
        """Test pipeline output can be summarized for Telegram (FR-025)."""
        from src.utils.formatters import MarkdownFormatter
        
        orchestrator = AlphaAgentOrchestrator(mock_config)
        report = await orchestrator.run()
        
        formatter = MarkdownFormatter(report)
        summary = formatter.format_summary(max_length=280)
        
        assert len(summary) <= 280
        assert "Alpha-Agent" in summary


class TestGitHubIssueReporter:
    """Integration tests for GitHub Issue posting."""
    
    @pytest.mark.asyncio
    async def test_post_report_creates_issue(self, mock_config):
        """Test posting report creates GitHub issue."""
        from src.delivery.github_issue import GitHubIssueReporter
        
        reporter = GitHubIssueReporter(
            token=mock_config.github_token or "",
            repository=mock_config.github_repository or "",
        )
        
        report = IntelligenceReport()
        report.technical_scans = [{"symbol": "TEST", "entry": 100, "target": 110, "stop_loss": 97.5, "rsi": 30, "confidence": 0.8, "universe": "QQQ"}]
        
        # Mock the HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"number": 42, "html_url": "https://github.com/test/repo/issues/42"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.get = AsyncMock(return_value=MagicMock(json=MagicMock(return_value=[]), raise_for_status=MagicMock()))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            result = await reporter.post_report(report)
            
            assert result["number"] == 42
            assert "github.com" in result["url"]


class TestTelegramNotifier:
    """Integration tests for Telegram notifications."""
    
    @pytest.mark.asyncio
    async def test_send_notification(self, mock_config):
        """Test sending Telegram notification."""
        from src.delivery.telegram_bot import TelegramNotifier
        
        notifier = TelegramNotifier(
            bot_token=mock_config.telegram_bot_token,
            chat_id=mock_config.telegram_chat_id,
        )
        
        report = IntelligenceReport()
        
        # Mock the HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            result = await notifier.send_report_notification(report, "https://example.com/issue/1")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_market_closed_notification(self, mock_config):
        """Test sending market closed notification."""
        from src.delivery.telegram_bot import TelegramNotifier
        
        notifier = TelegramNotifier(
            bot_token=mock_config.telegram_bot_token,
            chat_id=mock_config.telegram_chat_id,
        )
        
        # Mock the HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            result = await notifier.send_market_closed_notification("New Year's Day")
            
            assert result is True
