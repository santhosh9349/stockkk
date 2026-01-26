"""Catalyst Macro Agent for event and indicator tracking.

Implements US4: Catalyst calendar intelligence + macro dashboard
Uses Gemini 3 Pro model for analysis.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from src.models import EventType, TimeBucket, Trend
from src.models.catalyst_event import CatalystEvent, create_catalyst_event
from src.models.macro_indicator import (
    MacroIndicator,
    create_dxy_indicator,
    create_treasury_indicator,
    create_cpi_indicator,
    create_fed_funds_indicator,
)
from src.tools.fred_data import FREDClient, MockFREDClient
from src.tools.market_calendar import MarketCalendar
from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class CatalystMacroAgent:
    """Catalyst and Macro Analysis Agent using Gemini 3 Pro.
    
    Implements:
    - Event categorization by time bucket (FR-014)
    - Macro dashboard (DXY, Treasury, CPI/PCE)
    - Market holiday detection for orchestrator
    """
    
    def __init__(self, config: Config):
        """Initialize agent with configuration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.calendar = MarketCalendar()
        
        # Use mock FRED client if no API key
        if config.fred_api_key:
            self.fred_client = FREDClient(api_key=config.fred_api_key)
        else:
            self.fred_client = MockFREDClient()
    
    async def analyze(self) -> tuple[list[dict], list[dict]]:
        """Run catalyst and macro analysis.
        
        Returns:
            Tuple of (catalysts list, macro_indicators list)
        """
        logger.info("Starting catalyst/macro analysis")
        
        # Get catalysts
        catalysts = await self._get_catalysts()
        
        # Get macro indicators
        macro_indicators = await self._get_macro_indicators()
        
        logger.info(
            f"Analysis complete: {len(catalysts)} catalysts, "
            f"{len(macro_indicators)} indicators"
        )
        
        return (
            [c.to_dict() for c in catalysts],
            [m.to_dict() for m in macro_indicators],
        )
    
    async def _get_catalysts(self) -> list[CatalystEvent]:
        """Get upcoming catalyst events.
        
        In production, this would fetch from earnings calendars,
        FDA calendar, Fed calendar, etc.
        
        Returns:
            List of catalyst events
        """
        # For MVP, return mock catalysts
        # In production, integrate with earnings calendar APIs
        today = date.today()
        
        catalysts = [
            create_catalyst_event(
                event_type=EventType.FED,
                title="FOMC Rate Decision",
                event_date=today + timedelta(days=14),
                details="Federal Reserve interest rate announcement",
                impact="HIGH",
                source="Federal Reserve",
            ),
            create_catalyst_event(
                event_type=EventType.ECONOMIC,
                title="CPI Release",
                event_date=today + timedelta(days=7),
                details="Consumer Price Index monthly data",
                impact="HIGH",
                source="BLS",
            ),
            create_catalyst_event(
                event_type=EventType.EARNINGS,
                title="AAPL Q1 Earnings",
                event_date=today + timedelta(days=3),
                symbol="AAPL",
                details="Apple quarterly earnings report",
                impact="HIGH",
                source="Company Calendar",
            ),
            create_catalyst_event(
                event_type=EventType.EARNINGS,
                title="NVDA Earnings",
                event_date=today + timedelta(days=21),
                symbol="NVDA",
                details="NVIDIA quarterly earnings report",
                impact="HIGH",
                source="Company Calendar",
            ),
        ]
        
        # Sort by date
        catalysts.sort(key=lambda x: x.event_date)
        
        return catalysts
    
    async def _get_macro_indicators(self) -> list[MacroIndicator]:
        """Get macro economic indicators.
        
        Returns:
            List of macro indicators with trends
        """
        indicators = []
        
        # Get DXY
        dxy_data = await self.fred_client.get_dxy()
        if dxy_data:
            current, previous = dxy_data
            indicators.append(create_dxy_indicator(current, previous))
        
        # Get 10Y Treasury
        treasury_data = await self.fred_client.get_treasury_10y()
        if treasury_data:
            current, previous = treasury_data
            indicators.append(create_treasury_indicator(current, previous))
        
        # Get CPI
        cpi_data = await self.fred_client.get_cpi()
        if cpi_data:
            current, previous = cpi_data
            indicators.append(create_cpi_indicator(current, previous))
        
        # Get Fed Funds
        fed_data = await self.fred_client.get_fed_funds()
        if fed_data:
            current, previous = fed_data
            indicators.append(create_fed_funds_indicator(current, previous))
        
        return indicators
    
    def is_market_holiday(self, check_date: Optional[date] = None) -> bool:
        """Check if date is a market holiday.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            True if market is closed for holiday
        """
        return self.calendar.is_market_holiday(check_date)
    
    def get_holiday_name(self, check_date: Optional[date] = None) -> Optional[str]:
        """Get holiday name if applicable.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            Holiday name or None
        """
        return self.calendar.get_holiday_name(check_date)
    
    def get_market_status(self, check_date: Optional[date] = None) -> dict:
        """Get comprehensive market status.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            Market status dict
        """
        return self.calendar.get_market_status(check_date)
    
    def get_macro_context(self) -> dict:
        """Get macro context for other agents.
        
        Returns summary of key macro indicators for use
        by other agents (especially MetalsAdvisor).
        
        Returns:
            Dict with key macro values
        """
        # This would normally use cached data from analyze()
        # For now, return placeholder
        return {
            "dxy_value": 104.25,
            "dxy_trend": Trend.STRENGTHENING,
            "treasury_10y": 4.35,
            "treasury_trend": Trend.NEUTRAL,
        }


async def run_catalyst_analysis(config: Config) -> tuple[list[dict], list[dict]]:
    """Convenience function to run catalyst/macro analysis.
    
    Args:
        config: Application configuration
        
    Returns:
        Tuple of (catalysts, macro_indicators)
    """
    agent = CatalystMacroAgent(config)
    return await agent.analyze()
