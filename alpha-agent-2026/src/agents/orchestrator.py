"""Alpha-Agent Orchestrator using Google ADK SequentialAgent.

Coordinates the execution of all investment intelligence agents
in a deterministic pipeline order.
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Any, Optional

from ..models.intelligence_report import IntelligenceReport, DataUnavailable
from ..models import ReportStatus
from ..utils.config import Config
from ..utils.retry import RetryExhausted

# Import agents
from .technical_scanner import TechnicalScannerAgent
from .portfolio_analyst import PortfolioAnalystAgent
from .catalyst_macro import CatalystMacroAgent
from .metals_advisor import MetalsAdvisorAgent

# Import tools
from ..tools.alpha_vantage import AlphaVantageClient, MockAlphaVantageClient
from ..tools.portfolio_reader import PortfolioReader
from ..tools.fred_data import FREDClient, MockFREDClient
from ..tools.news_sentiment import NewsSentimentClient, MockNewsSentimentClient
from ..tools.market_calendar import MarketCalendar

logger = logging.getLogger(__name__)


class AlphaAgentOrchestrator:
    """Orchestrates the Alpha-Agent pipeline.
    
    Executes agents in sequence:
    1. TechnicalScanner (breakout detection)
    2. PortfolioAnalyst (health monitoring)
    3. CatalystMacro (event calendar + macro)
    4. MetalsAdvisor (Gold/Silver timing)
    
    Implements partial report fallback (FR-026) when agents fail.
    """
    
    def __init__(self, config: Config, dry_run: bool = False):
        """Initialize orchestrator with configuration.
        
        Args:
            config: Application configuration
            dry_run: If True, use mock clients instead of real APIs
        """
        self.config = config
        self.dry_run = dry_run
        self.report = IntelligenceReport()
        
        # Initialize tools based on dry_run mode
        self._init_tools()
        
        # Initialize agents
        self._init_agents()
    
    def _init_tools(self) -> None:
        """Initialize data tools (MCP-compliant, read-only)."""
        if self.dry_run:
            self._alpha_vantage = MockAlphaVantageClient()
            self._fred_client = MockFREDClient()
            self._news_client = MockNewsSentimentClient()
        else:
            self._alpha_vantage = AlphaVantageClient(
                api_key=self.config.alpha_vantage_api_key
            )
            self._fred_client = FREDClient(
                api_key=self.config.fred_api_key
            )
            self._news_client = NewsSentimentClient(
                finnhub_api_key=self.config.finnhub_api_key
            )
        
        self._portfolio_reader = PortfolioReader(
            portfolio_path=self.config.portfolio_path
        )
        self._market_calendar = MarketCalendar()
    
    def _init_agents(self) -> None:
        """Initialize all agents with their respective tools."""
        self._technical_scanner = TechnicalScannerAgent(
            config=self.config
        )
        self._portfolio_analyst = PortfolioAnalystAgent(
            config=self.config
        )
        self._catalyst_macro = CatalystMacroAgent(
            config=self.config
        )
        self._metals_advisor = MetalsAdvisorAgent(
            config=self.config
        )
    
    async def run(self, market_closed: bool = False) -> IntelligenceReport:
        """Execute the full agent pipeline.
        
        Args:
            market_closed: If True, skip agents and return market closed notice
        
        Returns:
            IntelligenceReport with all agent results
        """
        logger.info("Starting Alpha-Agent pipeline...")
        start_time = datetime.now()
        
        # Handle market closed mode (FR-027)
        if market_closed:
            logger.info("Market closed mode - skipping agents")
            self.report.mark_market_closed()
            return self.report
        
        # Execute agents in sequence
        # Each agent populates its section of the report
        # Failures are caught and marked as unavailable (FR-026)
        
        await self._run_technical_scanner()
        await self._run_portfolio_analyst()
        await self._run_catalyst_macro()
        await self._run_metals_advisor()
        
        # Log completion
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Pipeline completed in {elapsed:.1f}s - Status: {self.report.status.value}")
        
        return self.report
    
    async def _run_technical_scanner(self) -> None:
        """Run Technical Scanner Agent (US2).
        
        Scans universe for RSI crossover and volume spike signals.
        Applies Constitution I (2.5% stop-loss) and Constitution III (biotech filter).
        """
        logger.info("Running Technical Scanner...")
        
        try:
            # Run scanner (scans all universes internally)
            recommendations = await self._technical_scanner.scan()
            
            # Convert to report format
            self.report.technical_scans = [
                {
                    "symbol": rec.ticker,
                    "universe": rec.universe.value if hasattr(rec.universe, 'value') else rec.universe,
                    "entry": rec.entry_price,
                    "target": rec.target_price,
                    "stop_loss": rec.stop_loss,
                    "rsi": rec.rsi,
                    "volume_ratio": rec.volume_ratio,
                    "confidence": rec.confidence,
                    "high_water_mark": rec.high_water_mark,
                }
                for rec in recommendations
            ]
            logger.info(f"Technical Scanner found {len(self.report.technical_scans)} candidates")
            
        except Exception as e:
            logger.error(f"Technical Scanner failed: {e}")
            self.report.mark_unavailable("technical_scans", str(e))
    
    async def _run_portfolio_analyst(self) -> None:
        """Run Portfolio Analyst Agent (US3).
        
        Analyzes portfolio holdings against 20-day SMA.
        Applies Constitution III Option B exit/hedge logic.
        """
        logger.info("Running Portfolio Analyst...")
        
        try:
            # Analyze portfolio
            holdings = await self._portfolio_analyst.analyze()
            
            # Convert to report format
            self.report.portfolio_alerts = [
                {
                    "symbol": holding.ticker,
                    "signal": holding.signal.value if hasattr(holding.signal, 'value') else holding.signal,
                    "pct_vs_sma": holding.pct_vs_sma,
                    "pnl_pct": holding.pnl_pct,
                    "position_pct": holding.position_pct,
                    "rationale": holding.rationale,
                }
                for holding in holdings
            ]
            logger.info(f"Portfolio Analyst generated {len(self.report.portfolio_alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Portfolio Analyst failed: {e}")
            self.report.mark_unavailable("portfolio_alerts", str(e))
    
    async def _run_catalyst_macro(self) -> None:
        """Run Catalyst & Macro Agent (US4).
        
        Placeholder implementation - returns mock data.
        Real implementation in T055-T058.
        """
        logger.info("Running Catalyst & Macro Agent...")
        
        try:
            # Get catalysts and macro data
            catalysts, macro_indicators = await self._catalyst_macro.analyze()
            
            # Convert catalysts to report format
            self.report.catalysts = [
                {
                    "ticker": cat.ticker,
                    "event_type": cat.event_type,
                    "description": cat.description,
                    "time_bucket": cat.time_bucket.value if hasattr(cat.time_bucket, 'value') else cat.time_bucket,
                    "date": str(cat.event_date),
                }
                for cat in catalysts
            ]
            
            # Convert macro indicators to report format
            self.report.macro_indicators = [
                {
                    "name": ind.name,
                    "value": ind.current_value,
                    "previous": ind.previous_value,
                    "trend": ind.trend.value if hasattr(ind.trend, 'value') else ind.trend,
                    "change_pct": ind.change_pct,
                }
                for ind in macro_indicators
            ]
            logger.info(f"Catalyst Agent found {len(self.report.catalysts)} events")
            
        except Exception as e:
            logger.error(f"Catalyst & Macro Agent failed: {e}")
            self.report.mark_unavailable("catalysts", str(e))
            self.report.mark_unavailable("macro_indicators", str(e))
    
    async def _run_metals_advisor(self) -> None:
        """Run Metals Advisor Agent (US5).
        
        Generates GLD/SLV recommendations with Constitution IV compliance.
        Requires DXY correlation and Treasury weighting.
        """
        logger.info("Running Metals Advisor...")
        
        try:
            # Get metals advice
            advice = await self._metals_advisor.advise()
            
            # Convert to report format (Constitution IV requires all fields)
            self.report.metals_advice = {
                "gld_action": advice.gld_action.value if hasattr(advice.gld_action, 'value') else advice.gld_action,
                "slv_action": advice.slv_action.value if hasattr(advice.slv_action, 'value') else advice.slv_action,
                "gld_price": advice.gld_price,
                "slv_price": advice.slv_price,
                "gld_rsi": advice.gld_rsi,
                "slv_rsi": advice.slv_rsi,
                "dxy_value": advice.dxy_value,
                "dxy_trend": advice.dxy_trend.value if hasattr(advice.dxy_trend, 'value') else advice.dxy_trend,
                "treasury_10y": advice.treasury_10y,
                "treasury_trend": advice.treasury_trend.value if hasattr(advice.treasury_trend, 'value') else advice.treasury_trend,
                "rationale": advice.rationale,
            }
            logger.info("Metals Advisor generated recommendation")
            
        except Exception as e:
            logger.error(f"Metals Advisor failed: {e}")
            self.report.mark_unavailable("metals_advice", str(e))
