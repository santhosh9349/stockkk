"""Technical Scanner Agent for breakout detection.

Implements US2: Scan QQQ/IBB/ITA/SPY for breakout candidates.
Uses Gemini 3 Flash model for fast technical analysis.

Constitution I Compliance:
- Every trade MUST specify Entry, Target, and Stop-Loss
- 2.5% trailing stop-loss with high_water_mark tracking

Constitution III Compliance (Biotech):
- IBB tickers filtered by $500M market cap minimum
"""

import asyncio
from typing import Optional
from datetime import datetime

from src.models import Universe
from src.models.trade_recommendation import TradeRecommendation, create_trade_recommendation
from src.tools.alpha_vantage import AlphaVantageClient, filter_tradeable_symbols
from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


# Hardcoded universe constituents for MVP
# In production, these would be fetched from ETF holdings
UNIVERSE_SYMBOLS = {
    Universe.QQQ: [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX",
        "AMD", "ADBE", "QCOM", "PEP", "CSCO", "INTC", "CMCSA", "TMUS", "INTU", "AMGN",
    ],
    Universe.IBB: [
        "VRTX", "GILD", "REGN", "MRNA", "BIIB", "ILMN", "SGEN", "ALNY", "BMRN", "SRPT",
        "EXAS", "BGNE", "IONS", "NBIX", "UTHR", "JAZZ", "RARE", "HZNP", "PCVX", "INSM",
    ],
    Universe.ITA: [
        "RTX", "BA", "LMT", "NOC", "GD", "LHX", "TDG", "HWM", "TXT", "HII",
        "LDOS", "KTOS", "AJRD", "SPR", "CW", "MOG.A", "DCO", "MRCY", "AVAV", "AXON",
    ],
    Universe.SPY: [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK.B", "UNH", "XOM", "JPM",
        "JNJ", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "LLY", "PFE",
    ],
}

# Biotech market cap threshold (Constitution III)
BIOTECH_MARKET_CAP_MIN = 500_000_000  # $500M


class TechnicalScannerAgent:
    """Technical Scanner Agent using Gemini 3 Flash.
    
    Scans universe ETFs for breakout candidates based on:
    - RSI crossover (< 30 oversold OR crossing 50 from below)
    - Volume spike (> 1.5x 20-day average)
    - Biotech filter ($500M min market cap for IBB)
    
    Constitution I: All recommendations include Entry, Target, Stop-Loss
    Constitution III: Biotech filtered by market cap
    """
    
    # Technical thresholds
    RSI_OVERSOLD = 30
    RSI_MOMENTUM = 50
    VOLUME_SPIKE_RATIO = 1.5
    
    # Output limits (FR-009)
    MAX_RECOMMENDATIONS = 10
    
    def __init__(self, config: Config):
        """Initialize scanner with configuration.
        
        Args:
            config: Application configuration with API keys
        """
        self.config = config
        self.client = AlphaVantageClient(
            api_key=config.alpha_vantage_api_key,
            cache_ttl_seconds=300,  # 5 minute cache
        )
        self._previous_rsi: dict[str, float] = {}  # Track RSI for crossover detection
    
    async def scan(self) -> list[TradeRecommendation]:
        """Run full technical scan across all universes.
        
        Returns:
            Top 10 trade recommendations ranked by confidence
        """
        logger.info("Starting technical scan across all universes")
        
        all_candidates: list[TradeRecommendation] = []
        
        # Scan each universe
        for universe in Universe:
            try:
                candidates = await self._scan_universe(universe)
                all_candidates.extend(candidates)
                logger.info(f"Found {len(candidates)} candidates in {universe.value}")
            except Exception as e:
                logger.error(f"Failed to scan {universe.value}: {e}")
                continue
        
        # Rank by confidence and limit to top 10 (FR-009)
        ranked = sorted(all_candidates, key=lambda x: x.confidence, reverse=True)
        top_picks = ranked[:self.MAX_RECOMMENDATIONS]
        
        logger.info(f"Scan complete: {len(top_picks)} recommendations from {len(all_candidates)} candidates")
        
        return top_picks
    
    async def _scan_universe(self, universe: Universe) -> list[TradeRecommendation]:
        """Scan a single universe for candidates.
        
        Args:
            universe: ETF universe to scan
            
        Returns:
            List of trade recommendations for this universe
        """
        symbols = UNIVERSE_SYMBOLS.get(universe, [])
        
        if not symbols:
            logger.warning(f"No symbols defined for {universe.value}")
            return []
        
        # Filter out halted/delisted stocks (FR-028)
        tradeable = await filter_tradeable_symbols(self.client, symbols)
        
        if len(tradeable) < len(symbols):
            logger.info(
                f"{universe.value}: Filtered {len(symbols) - len(tradeable)} "
                f"halted/delisted symbols"
            )
        
        candidates = []
        
        for symbol in tradeable:
            try:
                recommendation = await self._analyze_symbol(symbol, universe)
                if recommendation:
                    candidates.append(recommendation)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        return candidates
    
    async def _analyze_symbol(
        self, symbol: str, universe: Universe
    ) -> Optional[TradeRecommendation]:
        """Analyze a single symbol for breakout potential.
        
        Args:
            symbol: Stock ticker symbol
            universe: ETF universe classification
            
        Returns:
            TradeRecommendation if breakout criteria met, None otherwise
        """
        # Apply biotech filter (Constitution III)
        if universe == Universe.IBB:
            if not await self._passes_biotech_filter(symbol):
                logger.debug(f"{symbol}: Failed biotech filter")
                return None
        
        # Get technical indicators
        rsi = await self.client.get_rsi(symbol)
        if rsi is None:
            return None
        
        # Check RSI criteria (T031)
        rsi_signal = self._check_rsi_criteria(symbol, rsi)
        if not rsi_signal:
            return None
        
        # Check volume criteria (T032)
        volume_ratio = await self._check_volume_criteria(symbol)
        if volume_ratio is None or volume_ratio < self.VOLUME_SPIKE_RATIO:
            return None
        
        # Get current price for entry calculation
        quote = await self.client.get_quote(symbol)
        if not quote or quote["price"] == 0:
            return None
        
        current_price = quote["price"]
        
        # Calculate trade parameters (T034)
        entry, target, confidence = self._calculate_trade_params(
            current_price, rsi, volume_ratio, rsi_signal
        )
        
        # Generate rationale
        rationale = self._generate_rationale(symbol, universe, rsi, volume_ratio, rsi_signal)
        
        # Create recommendation with Constitution I compliance
        return create_trade_recommendation(
            symbol=symbol,
            universe=universe,
            entry=entry,
            target=target,
            rsi=rsi,
            confidence=confidence,
            rationale=rationale,
            volume_ratio=volume_ratio,
        )
    
    async def _passes_biotech_filter(self, symbol: str) -> bool:
        """Check if biotech stock passes $500M market cap filter (T033).
        
        Constitution III: IBB tickers MUST have market cap >= $500M
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            True if passes filter, False otherwise
        """
        market_cap = await self.client.get_market_cap(symbol)
        
        if market_cap is None:
            logger.warning(f"{symbol}: Unable to retrieve market cap, excluding")
            return False
        
        passes = market_cap >= BIOTECH_MARKET_CAP_MIN
        
        if not passes:
            logger.debug(
                f"{symbol}: Market cap ${market_cap/1e6:.1f}M < "
                f"${BIOTECH_MARKET_CAP_MIN/1e6:.1f}M threshold"
            )
        
        return passes
    
    def _check_rsi_criteria(self, symbol: str, current_rsi: float) -> Optional[str]:
        """Check RSI breakout criteria (T031).
        
        Criteria:
        - RSI < 30 (oversold)
        - RSI crossing 50 from below (momentum shift)
        
        Args:
            symbol: Stock ticker for tracking
            current_rsi: Current RSI value
            
        Returns:
            Signal type ("oversold" or "momentum") if criteria met, None otherwise
        """
        previous_rsi = self._previous_rsi.get(symbol)
        self._previous_rsi[symbol] = current_rsi
        
        # Check oversold condition
        if current_rsi < self.RSI_OVERSOLD:
            return "oversold"
        
        # Check momentum crossover
        if previous_rsi is not None:
            if previous_rsi < self.RSI_MOMENTUM and current_rsi >= self.RSI_MOMENTUM:
                return "momentum"
        
        return None
    
    async def _check_volume_criteria(self, symbol: str) -> Optional[float]:
        """Check volume spike criteria (T032).
        
        Volume must be > 1.5x 20-day average.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Volume ratio if available, None otherwise
        """
        volumes = await self.client.get_daily_volume(symbol, days=21)
        
        if not volumes or len(volumes) < 2:
            return None
        
        # Current day volume vs average of previous 20 days
        current_volume = volumes[0]
        avg_volume = sum(volumes[1:21]) / min(len(volumes) - 1, 20)
        
        if avg_volume == 0:
            return None
        
        return current_volume / avg_volume
    
    def _calculate_trade_params(
        self,
        current_price: float,
        rsi: float,
        volume_ratio: float,
        signal_type: str,
    ) -> tuple[float, float, float]:
        """Calculate trade entry, target, and confidence (T034).
        
        Constitution I: Entry, Target, and 2.5% Stop-Loss calculated.
        
        Args:
            current_price: Current market price
            rsi: RSI indicator value
            volume_ratio: Volume vs average
            signal_type: Type of signal (oversold/momentum)
            
        Returns:
            Tuple of (entry, target, confidence)
        """
        # Entry at current price
        entry = current_price
        
        # Target based on signal type and technical strength
        if signal_type == "oversold":
            # Oversold bounce targets 10-15% gain
            target_pct = 0.10 + (0.05 * (30 - rsi) / 30)  # More upside if more oversold
        else:  # momentum
            # Momentum continuation targets 5-10% gain
            target_pct = 0.05 + (0.05 * min(volume_ratio - 1.5, 1))
        
        target = entry * (1 + target_pct)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(rsi, volume_ratio, signal_type)
        
        return entry, target, confidence
    
    def _calculate_confidence(
        self,
        rsi: float,
        volume_ratio: float,
        signal_type: str,
    ) -> float:
        """Calculate confidence score for ranking (T035).
        
        Confidence factors:
        - RSI extremity (more oversold = higher confidence)
        - Volume strength (higher ratio = higher confidence)
        - Signal type (oversold typically more reliable)
        
        Args:
            rsi: RSI indicator value
            volume_ratio: Volume vs average
            signal_type: Type of signal
            
        Returns:
            Confidence score (0.0 - 1.0)
        """
        # Base confidence by signal type
        base = 0.6 if signal_type == "oversold" else 0.5
        
        # RSI contribution (more extreme = more confident)
        if signal_type == "oversold":
            rsi_factor = (30 - rsi) / 30 * 0.2  # 0-0.2 based on how oversold
        else:
            rsi_factor = 0.1  # Momentum gets modest RSI boost
        
        # Volume contribution (stronger volume = more confident)
        volume_factor = min((volume_ratio - 1.5) / 2.5, 1) * 0.2  # 0-0.2 for 1.5x-4x volume
        
        confidence = min(base + rsi_factor + volume_factor, 1.0)
        
        return round(confidence, 2)
    
    def _generate_rationale(
        self,
        symbol: str,
        universe: Universe,
        rsi: float,
        volume_ratio: float,
        signal_type: str,
    ) -> str:
        """Generate human-readable rationale for recommendation.
        
        Args:
            symbol: Stock ticker
            universe: ETF universe
            rsi: RSI value
            volume_ratio: Volume vs average
            signal_type: Signal type
            
        Returns:
            Rationale string
        """
        if signal_type == "oversold":
            signal_desc = f"RSI at {rsi:.1f} indicates oversold conditions"
        else:
            signal_desc = f"RSI crossed above 50, indicating momentum shift"
        
        volume_desc = f"Volume {volume_ratio:.1f}x average confirms institutional interest"
        
        return f"{symbol} ({universe.value}): {signal_desc}. {volume_desc}."


async def run_technical_scan(config: Config) -> list[TradeRecommendation]:
    """Convenience function to run technical scan.
    
    Args:
        config: Application configuration
        
    Returns:
        List of trade recommendations
    """
    scanner = TechnicalScannerAgent(config)
    return await scanner.scan()
