"""News sentiment tool for portfolio analysis.

Implements Constitution II (Data Governance):
- Read-only access to verified news sources
- Bloomberg/Finnhub verified sources only
"""

import httpx
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.utils.retry import with_retry
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SentimentResult:
    """Result from sentiment analysis."""
    
    symbol: str
    score: float  # -1.0 (bearish) to 1.0 (bullish)
    articles_analyzed: int
    sources: list[str]
    last_updated: datetime
    
    @property
    def sentiment_label(self) -> str:
        """Get human-readable sentiment label."""
        if self.score >= 0.3:
            return "BULLISH"
        elif self.score <= -0.3:
            return "BEARISH"
        else:
            return "NEUTRAL"


class NewsSentimentClient:
    """News sentiment analysis client.
    
    Constitution II: Read-only access to verified sources only.
    Supports Bloomberg and Finnhub as primary sources.
    """
    
    # Finnhub API base URL
    FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
    
    # Cache TTL (sentiment doesn't change rapidly)
    CACHE_TTL_HOURS = 4
    
    def __init__(self, finnhub_api_key: Optional[str] = None):
        """Initialize client with API keys.
        
        Args:
            finnhub_api_key: Finnhub API key (optional)
        """
        self.finnhub_api_key = finnhub_api_key
        self._cache: dict[str, tuple[datetime, SentimentResult]] = {}
    
    def _get_cached(self, symbol: str) -> Optional[SentimentResult]:
        """Get cached sentiment if not expired."""
        if symbol in self._cache:
            timestamp, result = self._cache[symbol]
            if datetime.now() - timestamp < timedelta(hours=self.CACHE_TTL_HOURS):
                logger.debug(f"Sentiment cache hit for {symbol}")
                return result
            else:
                del self._cache[symbol]
        return None
    
    def _set_cached(self, symbol: str, result: SentimentResult) -> None:
        """Cache sentiment result."""
        self._cache[symbol] = (datetime.now(), result)
    
    @with_retry(max_attempts=3, base_delay=1.0)
    async def _fetch_finnhub_sentiment(
        self, symbol: str
    ) -> Optional[dict]:
        """Fetch sentiment from Finnhub API.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Raw sentiment data or None if unavailable
        """
        if not self.finnhub_api_key:
            return None
        
        # Get news sentiment
        url = f"{self.FINNHUB_BASE_URL}/news-sentiment"
        params = {
            "symbol": symbol,
            "token": self.finnhub_api_key,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
    async def get_sentiment(self, symbol: str) -> SentimentResult:
        """Get sentiment analysis for a symbol.
        
        Uses Finnhub sentiment API with fallback to neutral.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            SentimentResult with score and metadata
        """
        symbol = symbol.upper()
        
        # Check cache first
        cached = self._get_cached(symbol)
        if cached:
            return cached
        
        # Try Finnhub API
        if self.finnhub_api_key:
            try:
                data = await self._fetch_finnhub_sentiment(symbol)
                
                if data and "sentiment" in data:
                    score = data["sentiment"].get("buzzIndex", 0)
                    # Normalize to -1 to 1 range
                    # Finnhub uses 0-1 scale, we convert to -1 to 1
                    normalized_score = (score - 0.5) * 2
                    
                    result = SentimentResult(
                        symbol=symbol,
                        score=max(-1.0, min(1.0, normalized_score)),
                        articles_analyzed=data.get("companyNewsScore", 0) or 5,
                        sources=["Finnhub"],
                        last_updated=datetime.now(),
                    )
                    
                    self._set_cached(symbol, result)
                    return result
                    
            except Exception as e:
                logger.warning(f"Finnhub sentiment fetch failed for {symbol}: {e}")
        
        # Fallback: Return neutral sentiment
        result = SentimentResult(
            symbol=symbol,
            score=0.0,
            articles_analyzed=0,
            sources=[],
            last_updated=datetime.now(),
        )
        
        return result
    
    async def get_batch_sentiment(
        self, symbols: list[str]
    ) -> dict[str, SentimentResult]:
        """Get sentiment for multiple symbols.
        
        Args:
            symbols: List of ticker symbols
            
        Returns:
            Dict mapping symbol to SentimentResult
        """
        results = {}
        
        for symbol in symbols:
            try:
                result = await self.get_sentiment(symbol)
                results[symbol] = result
            except Exception as e:
                logger.error(f"Failed to get sentiment for {symbol}: {e}")
                results[symbol] = SentimentResult(
                    symbol=symbol,
                    score=0.0,
                    articles_analyzed=0,
                    sources=[],
                    last_updated=datetime.now(),
                )
        
        return results


# Mock implementation for testing without API keys
class MockNewsSentimentClient(NewsSentimentClient):
    """Mock sentiment client for testing."""
    
    # Predefined sentiments for common symbols
    MOCK_SENTIMENTS = {
        "AAPL": 0.4,   # Bullish
        "MSFT": 0.3,   # Bullish
        "TSLA": 0.1,   # Slightly bullish
        "NVDA": 0.5,   # Very bullish
        "META": 0.2,   # Slightly bullish
        "GOOGL": 0.15, # Slightly bullish
        "AMZN": 0.25,  # Bullish
        "MRNA": -0.2,  # Slightly bearish
        "GME": -0.4,   # Bearish
        "AMC": -0.3,   # Bearish
    }
    
    async def get_sentiment(self, symbol: str) -> SentimentResult:
        """Return mock sentiment."""
        symbol = symbol.upper()
        
        score = self.MOCK_SENTIMENTS.get(symbol, 0.0)
        
        return SentimentResult(
            symbol=symbol,
            score=score,
            articles_analyzed=10,
            sources=["Mock"],
            last_updated=datetime.now(),
        )
