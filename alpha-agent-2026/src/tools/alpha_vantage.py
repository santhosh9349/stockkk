"""Alpha Vantage API tool for financial data retrieval.

Implements MCP-compliant read-only tool per Constitution II (Data Governance).
Includes halted/delisted stock detection per FR-028.
"""

import httpx
import asyncio
from typing import Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from src.utils.retry import with_retry
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimiter:
    """Rate limiter for Alpha Vantage API (5 calls/min free tier)."""
    
    max_calls: int = 5
    window_seconds: int = 60
    calls: list = field(default_factory=list)
    
    async def acquire(self) -> None:
        """Wait if rate limit would be exceeded."""
        now = datetime.now()
        # Remove calls outside window
        self.calls = [t for t in self.calls if now - t < timedelta(seconds=self.window_seconds)]
        
        if len(self.calls) >= self.max_calls:
            # Wait until oldest call expires
            oldest = min(self.calls)
            wait_time = self.window_seconds - (now - oldest).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        self.calls.append(datetime.now())


class StockStatus:
    """Stock trading status information."""
    
    ACTIVE = "ACTIVE"
    HALTED = "HALTED"
    DELISTED = "DELISTED"
    UNKNOWN = "UNKNOWN"


@dataclass
class StockStatusResult:
    """Result of stock status check."""
    
    symbol: str
    status: str
    reason: Optional[str] = None
    last_trade_date: Optional[str] = None
    
    @property
    def is_tradeable(self) -> bool:
        """Check if stock can be traded."""
        return self.status == StockStatus.ACTIVE


class AlphaVantageClient:
    """Alpha Vantage API client with rate limiting and caching.
    
    Implements FR-028: Halted/delisted stock detection and skip logic.
    """
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str, cache_ttl_seconds: int = 300):
        """Initialize client with API key.
        
        Args:
            api_key: Alpha Vantage API key
            cache_ttl_seconds: Cache TTL in seconds (default 5 minutes)
        """
        self.api_key = api_key
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.rate_limiter = RateLimiter()
        self._cache: dict[str, tuple[datetime, Any]] = {}
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            timestamp, value = self._cache[key]
            if datetime.now() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit for {key}")
                return value
            else:
                del self._cache[key]
        return None
    
    def _set_cached(self, key: str, value: Any) -> None:
        """Set cached value with timestamp."""
        self._cache[key] = (datetime.now(), value)
    
    @with_retry(max_attempts=3, base_delay=1.0)
    async def _request(self, params: dict[str, str]) -> dict[str, Any]:
        """Make API request with rate limiting and retry.
        
        Args:
            params: Query parameters (without apikey)
            
        Returns:
            JSON response as dict
            
        Raises:
            httpx.HTTPStatusError: On API errors
            ValueError: On API error responses
        """
        await self.rate_limiter.acquire()
        
        params["apikey"] = self.api_key
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check for API error messages
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
            if "Note" in data and "API call frequency" in data["Note"]:
                raise ValueError("Alpha Vantage rate limit exceeded")
            
            return data
    
    async def check_stock_status(self, symbol: str) -> StockStatusResult:
        """Check if stock is halted or delisted (FR-028).
        
        Uses GLOBAL_QUOTE to determine if a stock is active.
        A stock is considered halted/delisted if:
        - No quote data available
        - Last trade date is more than 5 business days old
        - API returns error for the symbol
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            StockStatusResult with status and details
        """
        cache_key = f"status_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            data = await self._request({
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
            })
            
            quote = data.get("Global Quote", {})
            
            if not quote or "01. symbol" not in quote:
                result = StockStatusResult(
                    symbol=symbol,
                    status=StockStatus.DELISTED,
                    reason="No quote data available - symbol may be delisted",
                )
            else:
                last_trade = quote.get("07. latest trading day", "")
                price = float(quote.get("05. price", 0))
                
                if price == 0:
                    result = StockStatusResult(
                        symbol=symbol,
                        status=StockStatus.HALTED,
                        reason="Zero price - trading may be halted",
                        last_trade_date=last_trade,
                    )
                elif last_trade:
                    # Check if last trade is too old (> 5 business days)
                    try:
                        last_date = datetime.strptime(last_trade, "%Y-%m-%d")
                        days_old = (datetime.now() - last_date).days
                        
                        if days_old > 7:  # ~5 business days
                            result = StockStatusResult(
                                symbol=symbol,
                                status=StockStatus.HALTED,
                                reason=f"Last trade {days_old} days ago - trading may be halted",
                                last_trade_date=last_trade,
                            )
                        else:
                            result = StockStatusResult(
                                symbol=symbol,
                                status=StockStatus.ACTIVE,
                                last_trade_date=last_trade,
                            )
                    except ValueError:
                        result = StockStatusResult(
                            symbol=symbol,
                            status=StockStatus.ACTIVE,
                            last_trade_date=last_trade,
                        )
                else:
                    result = StockStatusResult(
                        symbol=symbol,
                        status=StockStatus.ACTIVE,
                    )
            
            self._set_cached(cache_key, result)
            
            if not result.is_tradeable:
                logger.warning(
                    f"Stock {symbol} is {result.status}: {result.reason}",
                    extra={"symbol": symbol, "status": result.status},
                )
            
            return result
            
        except ValueError as e:
            # API error - symbol likely doesn't exist
            logger.warning(f"API error checking {symbol}: {e}")
            return StockStatusResult(
                symbol=symbol,
                status=StockStatus.UNKNOWN,
                reason=str(e),
            )
        except Exception as e:
            logger.error(f"Failed to check status for {symbol}: {e}")
            return StockStatusResult(
                symbol=symbol,
                status=StockStatus.UNKNOWN,
                reason=f"Check failed: {e}",
            )
    
    async def get_quote(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get current quote for a symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Quote data dict or None if unavailable
        """
        cache_key = f"quote_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            data = await self._request({
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
            })
            
            quote = data.get("Global Quote", {})
            if quote:
                result = {
                    "symbol": quote.get("01. symbol"),
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": quote.get("10. change percent", "0%"),
                    "volume": int(quote.get("06. volume", 0)),
                    "latest_trading_day": quote.get("07. latest trading day"),
                }
                self._set_cached(cache_key, result)
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    async def get_rsi(
        self, symbol: str, interval: str = "daily", time_period: int = 14
    ) -> Optional[float]:
        """Get RSI indicator value.
        
        Args:
            symbol: Stock ticker symbol
            interval: Time interval (daily, weekly, monthly)
            time_period: Number of periods for RSI calculation
            
        Returns:
            Latest RSI value or None if unavailable
        """
        cache_key = f"rsi_{symbol}_{interval}_{time_period}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            data = await self._request({
                "function": "RSI",
                "symbol": symbol,
                "interval": interval,
                "time_period": str(time_period),
                "series_type": "close",
            })
            
            rsi_data = data.get("Technical Analysis: RSI", {})
            if rsi_data:
                # Get most recent RSI value
                latest_date = sorted(rsi_data.keys(), reverse=True)[0]
                rsi_value = float(rsi_data[latest_date]["RSI"])
                self._set_cached(cache_key, rsi_value)
                return rsi_value
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get RSI for {symbol}: {e}")
            return None
    
    async def get_sma(
        self, symbol: str, interval: str = "daily", time_period: int = 20
    ) -> Optional[float]:
        """Get SMA indicator value.
        
        Args:
            symbol: Stock ticker symbol
            interval: Time interval (daily, weekly, monthly)
            time_period: Number of periods for SMA calculation
            
        Returns:
            Latest SMA value or None if unavailable
        """
        cache_key = f"sma_{symbol}_{interval}_{time_period}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            data = await self._request({
                "function": "SMA",
                "symbol": symbol,
                "interval": interval,
                "time_period": str(time_period),
                "series_type": "close",
            })
            
            sma_data = data.get("Technical Analysis: SMA", {})
            if sma_data:
                latest_date = sorted(sma_data.keys(), reverse=True)[0]
                sma_value = float(sma_data[latest_date]["SMA"])
                self._set_cached(cache_key, sma_value)
                return sma_value
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get SMA for {symbol}: {e}")
            return None
    
    async def get_daily_volume(
        self, symbol: str, days: int = 20
    ) -> Optional[list[int]]:
        """Get daily volume data for calculating average.
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days to retrieve
            
        Returns:
            List of daily volumes or None if unavailable
        """
        cache_key = f"volume_{symbol}_{days}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            data = await self._request({
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
            })
            
            time_series = data.get("Time Series (Daily)", {})
            if time_series:
                dates = sorted(time_series.keys(), reverse=True)[:days]
                volumes = [
                    int(time_series[date]["5. volume"])
                    for date in dates
                ]
                self._set_cached(cache_key, volumes)
                return volumes
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get volume for {symbol}: {e}")
            return None
    
    async def get_market_cap(self, symbol: str) -> Optional[float]:
        """Get market capitalization for biotech filter.
        
        Uses OVERVIEW endpoint for fundamental data.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Market cap in USD or None if unavailable
        """
        cache_key = f"marketcap_{symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            data = await self._request({
                "function": "OVERVIEW",
                "symbol": symbol,
            })
            
            market_cap_str = data.get("MarketCapitalization", "0")
            if market_cap_str:
                market_cap = float(market_cap_str)
                self._set_cached(cache_key, market_cap)
                return market_cap
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get market cap for {symbol}: {e}")
            return None


async def filter_tradeable_symbols(
    client: AlphaVantageClient, symbols: list[str]
) -> list[str]:
    """Filter symbols to only those that are tradeable (FR-028).
    
    Removes halted and delisted symbols from the list.
    
    Args:
        client: Alpha Vantage client instance
        symbols: List of symbols to filter
        
    Returns:
        List of tradeable symbols only
    """
    tradeable = []
    
    for symbol in symbols:
        status = await client.check_stock_status(symbol)
        if status.is_tradeable:
            tradeable.append(symbol)
        else:
            logger.info(
                f"Excluding {symbol} from scan: {status.status}",
                extra={"symbol": symbol, "reason": status.reason},
            )
    
    return tradeable
