"""FRED Data API tool for macro economic data.

Implements Constitution II (Data Governance):
- Read-only access to FRED API
- Daily caching for rate limit compliance
"""

import httpx
import asyncio
from typing import Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.utils.retry import with_retry
from src.utils.logging import get_logger

logger = get_logger(__name__)


# FRED Series IDs
FRED_SERIES = {
    "DXY": "DTWEXBGS",  # Trade Weighted U.S. Dollar Index
    "TREASURY_10Y": "DGS10",  # 10-Year Treasury Constant Maturity Rate
    "CPI": "CPIAUCSL",  # Consumer Price Index
    "PCE": "PCEPI",  # Personal Consumption Expenditures Price Index
    "FED_FUNDS": "FEDFUNDS",  # Effective Federal Funds Rate
}


@dataclass
class FREDDataPoint:
    """A single FRED data point."""
    
    series_id: str
    value: float
    date: str
    realtime_start: str


class FREDClient:
    """FRED API client with caching.
    
    Constitution II: Read-only access to macro economic data.
    Implements daily caching to minimize API calls.
    """
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    # Cache for 24 hours (FRED data updates daily)
    CACHE_TTL_HOURS = 24
    
    def __init__(self, api_key: str):
        """Initialize client with API key.
        
        Args:
            api_key: FRED API key
        """
        self.api_key = api_key
        self._cache: dict[str, tuple[datetime, Any]] = {}
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            timestamp, value = self._cache[key]
            if datetime.now() - timestamp < timedelta(hours=self.CACHE_TTL_HOURS):
                logger.debug(f"FRED cache hit for {key}")
                return value
            else:
                del self._cache[key]
        return None
    
    def _set_cached(self, key: str, value: Any) -> None:
        """Cache value with timestamp."""
        self._cache[key] = (datetime.now(), value)
    
    @with_retry(max_attempts=3, base_delay=1.0)
    async def _request(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        """Make API request with retry.
        
        Args:
            endpoint: API endpoint
            params: Query parameters (without api_key)
            
        Returns:
            JSON response
        """
        params["api_key"] = self.api_key
        params["file_type"] = "json"
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
    async def get_latest_observation(self, series_id: str) -> Optional[FREDDataPoint]:
        """Get latest observation for a series.
        
        Args:
            series_id: FRED series identifier
            
        Returns:
            Latest data point or None if unavailable
        """
        cache_key = f"latest_{series_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            data = await self._request("series/observations", {
                "series_id": series_id,
                "sort_order": "desc",
                "limit": "1",
            })
            
            observations = data.get("observations", [])
            if observations:
                obs = observations[0]
                value = obs.get("value", ".")
                
                # Handle missing values (FRED uses "." for missing)
                if value == "." or value is None:
                    return None
                
                result = FREDDataPoint(
                    series_id=series_id,
                    value=float(value),
                    date=obs.get("date", ""),
                    realtime_start=obs.get("realtime_start", ""),
                )
                
                self._set_cached(cache_key, result)
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get {series_id} from FRED: {e}")
            return None
    
    async def get_previous_observation(self, series_id: str) -> Optional[FREDDataPoint]:
        """Get previous observation for trend calculation.
        
        Args:
            series_id: FRED series identifier
            
        Returns:
            Previous data point or None if unavailable
        """
        cache_key = f"previous_{series_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            data = await self._request("series/observations", {
                "series_id": series_id,
                "sort_order": "desc",
                "limit": "2",
            })
            
            observations = data.get("observations", [])
            if len(observations) >= 2:
                obs = observations[1]  # Second most recent
                value = obs.get("value", ".")
                
                if value == "." or value is None:
                    return None
                
                result = FREDDataPoint(
                    series_id=series_id,
                    value=float(value),
                    date=obs.get("date", ""),
                    realtime_start=obs.get("realtime_start", ""),
                )
                
                self._set_cached(cache_key, result)
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get previous {series_id} from FRED: {e}")
            return None
    
    async def get_dxy(self) -> Optional[tuple[float, Optional[float]]]:
        """Get DXY (Dollar Index) value and previous.
        
        Returns:
            Tuple of (current, previous) values
        """
        series_id = FRED_SERIES["DXY"]
        
        current = await self.get_latest_observation(series_id)
        previous = await self.get_previous_observation(series_id)
        
        if current:
            return (current.value, previous.value if previous else None)
        return None
    
    async def get_treasury_10y(self) -> Optional[tuple[float, Optional[float]]]:
        """Get 10Y Treasury yield and previous.
        
        Returns:
            Tuple of (current, previous) values
        """
        series_id = FRED_SERIES["TREASURY_10Y"]
        
        current = await self.get_latest_observation(series_id)
        previous = await self.get_previous_observation(series_id)
        
        if current:
            return (current.value, previous.value if previous else None)
        return None
    
    async def get_cpi(self) -> Optional[tuple[float, Optional[float]]]:
        """Get CPI value and previous.
        
        Returns:
            Tuple of (current, previous) values
        """
        series_id = FRED_SERIES["CPI"]
        
        current = await self.get_latest_observation(series_id)
        previous = await self.get_previous_observation(series_id)
        
        if current:
            return (current.value, previous.value if previous else None)
        return None
    
    async def get_pce(self) -> Optional[tuple[float, Optional[float]]]:
        """Get PCE value and previous.
        
        Returns:
            Tuple of (current, previous) values
        """
        series_id = FRED_SERIES["PCE"]
        
        current = await self.get_latest_observation(series_id)
        previous = await self.get_previous_observation(series_id)
        
        if current:
            return (current.value, previous.value if previous else None)
        return None
    
    async def get_fed_funds(self) -> Optional[tuple[float, Optional[float]]]:
        """Get Fed Funds Rate and previous.
        
        Returns:
            Tuple of (current, previous) values
        """
        series_id = FRED_SERIES["FED_FUNDS"]
        
        current = await self.get_latest_observation(series_id)
        previous = await self.get_previous_observation(series_id)
        
        if current:
            return (current.value, previous.value if previous else None)
        return None


# Mock client for testing
class MockFREDClient(FREDClient):
    """Mock FRED client for testing without API key."""
    
    MOCK_DATA = {
        "DXY": (104.25, 103.80),
        "TREASURY_10Y": (4.35, 4.28),
        "CPI": (3.2, 3.4),
        "PCE": (2.8, 2.9),
        "FED_FUNDS": (5.33, 5.33),
    }
    
    def __init__(self, api_key: str = "mock"):
        """Initialize mock client."""
        self.api_key = api_key
        self._cache = {}
    
    async def get_dxy(self) -> Optional[tuple[float, Optional[float]]]:
        """Return mock DXY data."""
        return self.MOCK_DATA["DXY"]
    
    async def get_treasury_10y(self) -> Optional[tuple[float, Optional[float]]]:
        """Return mock Treasury data."""
        return self.MOCK_DATA["TREASURY_10Y"]
    
    async def get_cpi(self) -> Optional[tuple[float, Optional[float]]]:
        """Return mock CPI data."""
        return self.MOCK_DATA["CPI"]
    
    async def get_pce(self) -> Optional[tuple[float, Optional[float]]]:
        """Return mock PCE data."""
        return self.MOCK_DATA["PCE"]
    
    async def get_fed_funds(self) -> Optional[tuple[float, Optional[float]]]:
        """Return mock Fed Funds data."""
        return self.MOCK_DATA["FED_FUNDS"]
