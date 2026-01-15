"""Portfolio Analyst Agent for health monitoring.

Implements US3: Analyze holdings, generate Exit/Hedge/Top-up signals.
Uses Gemini 3 Pro model for portfolio analysis.

Constitution III Compliance:
- Option B: EXIT if position > 10% OR loss > 10%, else HEDGE
- Sentiment cross-reference with verified news sources
"""

import asyncio
from typing import Optional
from pathlib import Path

from src.models import Signal
from src.models.portfolio_holding import PortfolioHolding, create_portfolio_holding
from src.tools.alpha_vantage import AlphaVantageClient
from src.tools.portfolio_reader import PortfolioReader, PortfolioHoldingSchema
from src.tools.news_sentiment import NewsSentimentClient, MockNewsSentimentClient
from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class PortfolioAnalystAgent:
    """Portfolio Health Monitoring Agent using Gemini 3 Pro.
    
    Analyzes portfolio holdings and generates signals based on:
    - Price vs 20-day SMA comparison (T043)
    - Option B Exit/Hedge logic (T044)
    - Top-up signal logic (T045)
    - News sentiment cross-reference (T046)
    
    Constitution III: Risk management through signal classification
    """
    
    def __init__(self, config: Config, portfolio_path: Optional[str] = None):
        """Initialize analyst with configuration.
        
        Args:
            config: Application configuration
            portfolio_path: Path to portfolio.json (optional override)
        """
        self.config = config
        self.portfolio_path = portfolio_path or config.portfolio_path
        
        # Initialize clients
        self.av_client = AlphaVantageClient(
            api_key=config.alpha_vantage_api_key,
            cache_ttl_seconds=300,
        )
        
        # Use mock sentiment if no API key
        if config.finnhub_api_key:
            self.sentiment_client = NewsSentimentClient(
                finnhub_api_key=config.finnhub_api_key
            )
        else:
            self.sentiment_client = MockNewsSentimentClient()
    
    async def analyze(self) -> list[dict]:
        """Run portfolio health analysis.
        
        Returns:
            List of portfolio alerts with signals and rationales
        """
        logger.info("Starting portfolio health analysis")
        
        # Load portfolio
        try:
            portfolio = self._load_portfolio()
        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")
            return []
        
        if not portfolio:
            logger.warning("No holdings found in portfolio")
            return []
        
        # Calculate total portfolio value for position % calculations
        total_value = await self._calculate_total_value(portfolio)
        
        if total_value == 0:
            logger.error("Unable to calculate portfolio value")
            return []
        
        # Analyze each holding
        alerts = []
        for holding in portfolio:
            try:
                alert = await self._analyze_holding(holding, total_value)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"Error analyzing {holding.symbol}: {e}")
                continue
        
        # Sort by signal priority (EXIT > HEDGE > TOP_UP > HOLD)
        signal_priority = {
            Signal.EXIT: 0,
            Signal.HEDGE: 1,
            Signal.TOP_UP: 2,
            Signal.HOLD: 3,
        }
        alerts.sort(key=lambda x: signal_priority.get(Signal(x["signal"]), 99))
        
        logger.info(f"Analysis complete: {len(alerts)} holdings analyzed")
        
        return alerts
    
    def _load_portfolio(self) -> list[PortfolioHoldingSchema]:
        """Load portfolio from JSON file.
        
        Returns:
            List of portfolio holdings
        """
        reader = PortfolioReader(self.portfolio_path)
        return reader.get_holdings()
    
    async def _calculate_total_value(
        self, holdings: list[PortfolioHoldingSchema]
    ) -> float:
        """Calculate total portfolio value using current prices.
        
        Args:
            holdings: List of holdings
            
        Returns:
            Total portfolio value
        """
        total = 0.0
        
        for holding in holdings:
            quote = await self.av_client.get_quote(holding.symbol)
            if quote and quote["price"] > 0:
                total += holding.shares * quote["price"]
            else:
                # Fallback to avg_cost
                total += holding.shares * holding.avg_cost
        
        return total
    
    async def _analyze_holding(
        self, holding: PortfolioHoldingSchema, total_portfolio_value: float
    ) -> Optional[dict]:
        """Analyze a single holding.
        
        Args:
            holding: Portfolio holding from JSON
            total_portfolio_value: Total portfolio value
            
        Returns:
            Alert dict with signal and rationale
        """
        symbol = holding.symbol
        
        # Get current price
        quote = await self.av_client.get_quote(symbol)
        if not quote or quote["price"] == 0:
            logger.warning(f"Unable to get quote for {symbol}")
            return None
        
        current_price = quote["price"]
        
        # Get 20-day SMA (T043)
        sma_20 = await self.av_client.get_sma(symbol, time_period=20)
        if sma_20 is None:
            logger.warning(f"Unable to get SMA for {symbol}")
            sma_20 = current_price  # Fallback to current price
        
        # Get sentiment (T046)
        sentiment = await self.sentiment_client.get_sentiment(symbol)
        
        # Create PortfolioHolding with computed properties
        portfolio_holding = create_portfolio_holding(
            symbol=symbol,
            shares=holding.shares,
            avg_cost=holding.avg_cost,
            current_price=current_price,
            sma_20=sma_20,
            total_portfolio_value=total_portfolio_value,
            sentiment_score=sentiment.score if sentiment else None,
            sector=holding.sector,
        )
        
        # Generate alert
        alert = portfolio_holding.to_alert_dict()
        
        # Add additional context
        alert["sentiment"] = {
            "score": sentiment.score if sentiment else 0.0,
            "label": sentiment.sentiment_label if sentiment else "NEUTRAL",
            "sources": sentiment.sources if sentiment else [],
        }
        
        return alert
    
    def _apply_option_b_logic(
        self, position_pct: float, pnl_pct: float, below_sma: bool
    ) -> Signal:
        """Apply Option B Exit/Hedge decision logic (T044).
        
        Constitution III Option B:
        - EXIT if position > 10% of portfolio
        - EXIT if loss > 10%
        - HEDGE if loss < 10% but below SMA
        
        Args:
            position_pct: Position as % of portfolio
            pnl_pct: Profit/loss percentage
            below_sma: Whether price is below 20-day SMA
            
        Returns:
            Trading signal
        """
        # EXIT conditions
        if position_pct > 10:
            return Signal.EXIT
        
        if pnl_pct < -10:
            return Signal.EXIT
        
        # HEDGE condition
        if pnl_pct < 0 and below_sma:
            return Signal.HEDGE
        
        return Signal.HOLD
    
    def _check_topup_conditions(
        self,
        pct_vs_sma: float,
        sentiment_score: Optional[float],
        pnl_pct: float,
    ) -> bool:
        """Check if top-up conditions are met (T045).
        
        Top-up conditions:
        - Positive momentum (price > 2% above SMA)
        - Favorable sentiment (score > 0.3)
        - Currently profitable (pnl > 0)
        
        Args:
            pct_vs_sma: Price vs SMA percentage
            sentiment_score: News sentiment score
            pnl_pct: Current P&L percentage
            
        Returns:
            True if top-up recommended
        """
        has_momentum = pct_vs_sma > 2
        has_favorable_sentiment = sentiment_score is not None and sentiment_score > 0.3
        is_profitable = pnl_pct > 0
        
        return has_momentum and has_favorable_sentiment and is_profitable


async def run_portfolio_analysis(config: Config) -> list[dict]:
    """Convenience function to run portfolio analysis.
    
    Args:
        config: Application configuration
        
    Returns:
        List of portfolio alerts
    """
    analyst = PortfolioAnalystAgent(config)
    return await analyst.analyze()
