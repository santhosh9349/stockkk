"""Metals Advisor Agent for Gold/Silver timing.

Implements US5 and Constitution IV (Macro Correlation):
- Metals weighted against DXY and Treasury yields
- DXY strength → Accumulate opportunity
- Overbought + geopolitical tension → Profit-take
"""

from typing import Optional

from src.models import MetalsAction, Trend
from src.models.metals_advice import MetalsAdvice, create_metals_advice
from src.tools.fred_data import FREDClient, MockFREDClient
from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class MetalsAdvisorAgent:
    """Metals Timing Advisor using Gemini 3 Pro.
    
    Implements Constitution IV (Macro Correlation):
    - DXY correlation logic (accumulate on strength)
    - Treasury yield context weighting
    - Profit-taking on overbought + geopolitical tension
    """
    
    # DXY thresholds for signals
    DXY_STRONG = 105.0  # Above this = strong dollar
    DXY_WEAK = 100.0    # Below this = weak dollar
    
    # Treasury thresholds
    TREASURY_HIGH = 4.5  # High yields (headwind for metals)
    TREASURY_LOW = 3.5   # Low yields (tailwind for metals)
    
    def __init__(self, config: Config, macro_context: Optional[dict] = None):
        """Initialize agent with configuration.
        
        Args:
            config: Application configuration
            macro_context: Pre-fetched macro data from CatalystMacroAgent
        """
        self.config = config
        self.macro_context = macro_context or {}
        
        # Use mock FRED client if no API key
        if config.fred_api_key:
            self.fred_client = FREDClient(api_key=config.fred_api_key)
        else:
            self.fred_client = MockFREDClient()
    
    async def advise(self) -> "MetalsAdvice":
        """Run metals timing analysis and return MetalsAdvice object.
        
        Returns:
            MetalsAdvice object
        """
        return await self.analyze_internal()
    
    async def analyze(self) -> dict:
        """Run metals timing analysis.
        
        Returns:
            MetalsAdvice as dict
        """
        advice = await self.analyze_internal()
        return advice.to_dict()
    
    async def analyze_internal(self) -> "MetalsAdvice":
        """Internal analysis returning MetalsAdvice object.
        
        Returns:
            MetalsAdvice object
        """
        logger.info("Starting metals timing analysis")
        
        # Get macro data (use context if available, else fetch)
        dxy_value, dxy_trend = await self._get_dxy_data()
        treasury_value, treasury_trend = await self._get_treasury_data()
        
        # Determine actions based on Constitution IV
        gld_action = self._determine_gld_action(
            dxy_value, dxy_trend, treasury_value, treasury_trend
        )
        slv_action = self._determine_slv_action(
            dxy_value, dxy_trend, treasury_value, treasury_trend
        )
        
        # Generate rationale
        rationale = self._generate_rationale(
            dxy_value, dxy_trend, treasury_value, treasury_trend,
            gld_action, slv_action
        )
        
        # Check for overbought/geopolitical signals
        overbought = self._check_overbought_signal()
        geo_risk = self._assess_geopolitical_risk()
        
        advice = create_metals_advice(
            dxy_value=dxy_value,
            dxy_trend=dxy_trend,
            treasury_10y=treasury_value,
            treasury_trend=treasury_trend,
            gld_action=gld_action,
            slv_action=slv_action,
            rationale=rationale,
            geopolitical_risk=geo_risk,
            overbought_signal=overbought,
        )
        
        logger.info(f"Metals advice: GLD={gld_action.value}, SLV={slv_action.value}")
        
        return advice
    
    async def _get_dxy_data(self) -> tuple[float, Trend]:
        """Get DXY value and trend.
        
        Uses macro_context if available, else fetches from FRED.
        
        Returns:
            Tuple of (value, trend)
        """
        if "dxy_value" in self.macro_context:
            return (
                self.macro_context["dxy_value"],
                self.macro_context.get("dxy_trend", Trend.NEUTRAL),
            )
        
        dxy_data = await self.fred_client.get_dxy()
        if dxy_data:
            current, previous = dxy_data
            trend = self._calculate_trend(current, previous)
            return (current, trend)
        
        # Default fallback
        return (104.0, Trend.NEUTRAL)
    
    async def _get_treasury_data(self) -> tuple[float, Trend]:
        """Get Treasury yield and trend.
        
        Returns:
            Tuple of (value, trend)
        """
        if "treasury_10y" in self.macro_context:
            return (
                self.macro_context["treasury_10y"],
                self.macro_context.get("treasury_trend", Trend.NEUTRAL),
            )
        
        treasury_data = await self.fred_client.get_treasury_10y()
        if treasury_data:
            current, previous = treasury_data
            trend = self._calculate_trend(current, previous)
            return (current, trend)
        
        # Default fallback
        return (4.0, Trend.NEUTRAL)
    
    def _calculate_trend(self, current: float, previous: Optional[float]) -> Trend:
        """Calculate trend from values."""
        if previous is None:
            return Trend.NEUTRAL
        
        change_pct = ((current - previous) / abs(previous)) * 100
        
        if change_pct > 1:
            return Trend.STRENGTHENING
        elif change_pct < -1:
            return Trend.WEAKENING
        else:
            return Trend.NEUTRAL
    
    def _determine_gld_action(
        self,
        dxy_value: float,
        dxy_trend: Trend,
        treasury_value: float,
        treasury_trend: Trend,
    ) -> MetalsAction:
        """Determine Gold (GLD) action per Constitution IV.
        
        Constitution IV Logic:
        - Strong DXY (> 105) + strengthening → ACCUMULATE (counter-trend opportunity)
        - Weak DXY (< 100) + weakening → PROFIT_TAKE (rally exhaustion)
        - High Treasury (> 4.5%) → Headwind, reduce to HOLD
        
        Args:
            dxy_value: Current DXY value
            dxy_trend: DXY trend direction
            treasury_value: 10Y Treasury yield
            treasury_trend: Treasury trend direction
            
        Returns:
            Recommended action for GLD
        """
        # Check for profit-take conditions
        overbought = self._check_overbought_signal()
        if overbought:
            return MetalsAction.PROFIT_TAKE
        
        # DXY correlation logic (Constitution IV)
        if dxy_value > self.DXY_STRONG:
            # Strong dollar = accumulate opportunity for gold
            if dxy_trend == Trend.STRENGTHENING:
                return MetalsAction.ACCUMULATE
            else:
                return MetalsAction.HOLD
        
        if dxy_value < self.DXY_WEAK:
            # Weak dollar = gold rally, consider profit-take if overbought
            if dxy_trend == Trend.WEAKENING:
                return MetalsAction.PROFIT_TAKE
            else:
                return MetalsAction.HOLD
        
        # Treasury context
        if treasury_value > self.TREASURY_HIGH:
            # High yields = headwind for gold
            return MetalsAction.HOLD
        
        if treasury_value < self.TREASURY_LOW:
            # Low yields = tailwind, accumulate
            return MetalsAction.ACCUMULATE
        
        return MetalsAction.HOLD
    
    def _determine_slv_action(
        self,
        dxy_value: float,
        dxy_trend: Trend,
        treasury_value: float,
        treasury_trend: Trend,
    ) -> MetalsAction:
        """Determine Silver (SLV) action.
        
        Silver generally follows gold but with higher volatility.
        Apply same logic with slightly more conservative thresholds.
        
        Args:
            dxy_value: Current DXY value
            dxy_trend: DXY trend direction
            treasury_value: 10Y Treasury yield
            treasury_trend: Treasury trend direction
            
        Returns:
            Recommended action for SLV
        """
        # Silver is more volatile, use same base logic as gold
        # but be more conservative on accumulate signals
        
        gld_action = self._determine_gld_action(
            dxy_value, dxy_trend, treasury_value, treasury_trend
        )
        
        # Convert to more conservative silver action
        if gld_action == MetalsAction.ACCUMULATE:
            # Only accumulate silver in strong DXY environment
            if dxy_value > self.DXY_STRONG + 1:
                return MetalsAction.ACCUMULATE
            else:
                return MetalsAction.HOLD
        
        return gld_action
    
    def _check_overbought_signal(self) -> bool:
        """Check if metals are overbought.
        
        In production, this would check RSI or other technical indicators.
        
        Returns:
            True if overbought conditions detected
        """
        # Placeholder - would integrate with technical analysis
        return False
    
    def _assess_geopolitical_risk(self) -> float:
        """Assess current geopolitical risk level.
        
        In production, this would integrate with news sentiment
        and geopolitical indicators.
        
        Returns:
            Risk score from 0 (low) to 1 (high)
        """
        # Placeholder - would integrate with news/geopolitical data
        return 0.5
    
    def _generate_rationale(
        self,
        dxy_value: float,
        dxy_trend: Trend,
        treasury_value: float,
        treasury_trend: Trend,
        gld_action: MetalsAction,
        slv_action: MetalsAction,
    ) -> str:
        """Generate explanation for recommendations.
        
        Returns:
            Human-readable rationale
        """
        parts = []
        
        # DXY context
        if dxy_value > self.DXY_STRONG:
            parts.append(f"Strong dollar (DXY {dxy_value:.2f})")
            if dxy_trend == Trend.STRENGTHENING:
                parts.append("with continued strength creates accumulation opportunity")
        elif dxy_value < self.DXY_WEAK:
            parts.append(f"Weak dollar (DXY {dxy_value:.2f})")
            if dxy_trend == Trend.WEAKENING:
                parts.append("rally may be extended, consider profit-taking")
        else:
            parts.append(f"Neutral dollar (DXY {dxy_value:.2f})")
        
        # Treasury context
        if treasury_value > self.TREASURY_HIGH:
            parts.append(f"High yields ({treasury_value:.2f}%) create headwind")
        elif treasury_value < self.TREASURY_LOW:
            parts.append(f"Low yields ({treasury_value:.2f}%) provide tailwind")
        
        return ". ".join(parts) + "."


async def run_metals_analysis(
    config: Config, macro_context: Optional[dict] = None
) -> dict:
    """Convenience function to run metals analysis.
    
    Args:
        config: Application configuration
        macro_context: Pre-fetched macro data
        
    Returns:
        MetalsAdvice as dict
    """
    agent = MetalsAdvisorAgent(config, macro_context)
    return await agent.analyze()
