"""Integration tests for FRED API tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.fred_data import FREDClient, MockFREDClient


class TestMockFREDClient:
    """Test mock FRED client for development."""
    
    @pytest.mark.asyncio
    async def test_mock_dxy(self):
        """Test mock DXY data."""
        client = MockFREDClient()
        result = await client.get_dxy()
        
        assert result is not None
        current, previous = result
        assert isinstance(current, float)
        assert current > 0
    
    @pytest.mark.asyncio
    async def test_mock_treasury(self):
        """Test mock Treasury data."""
        client = MockFREDClient()
        result = await client.get_treasury_10y()
        
        assert result is not None
        current, previous = result
        assert isinstance(current, float)
        assert current > 0
    
    @pytest.mark.asyncio
    async def test_mock_cpi(self):
        """Test mock CPI data."""
        client = MockFREDClient()
        result = await client.get_cpi()
        
        assert result is not None
        current, previous = result
        assert isinstance(current, float)
    
    @pytest.mark.asyncio
    async def test_mock_fed_funds(self):
        """Test mock Fed Funds data."""
        client = MockFREDClient()
        result = await client.get_fed_funds()
        
        assert result is not None
        current, previous = result
        assert isinstance(current, float)


class TestFREDClientCaching:
    """Test FRED client caching behavior."""
    
    @pytest.mark.asyncio
    async def test_cache_prevents_duplicate_requests(self):
        """Test that caching prevents duplicate API calls."""
        client = FREDClient(api_key="test_key")
        
        # Mock the API request
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {
                "observations": [
                    {"value": "104.5", "date": "2026-01-15", "realtime_start": "2026-01-15"}
                ]
            }
            
            # First call should hit API
            result1 = await client.get_latest_observation("DTWEXBGS")
            assert mock_request.call_count == 1
            
            # Second call should use cache
            result2 = await client.get_latest_observation("DTWEXBGS")
            assert mock_request.call_count == 1  # Still 1, not 2
            
            # Results should be equal
            assert result1 == result2


class TestFREDDataPoint:
    """Test FRED data point structure."""
    
    @pytest.mark.asyncio
    async def test_data_point_values(self):
        """Test data point has correct values."""
        from src.tools.fred_data import FREDDataPoint
        
        point = FREDDataPoint(
            series_id="TEST",
            value=104.25,
            date="2026-01-15",
            realtime_start="2026-01-15",
        )
        
        assert point.series_id == "TEST"
        assert point.value == 104.25
        assert point.date == "2026-01-15"


class TestFREDSeriesMapping:
    """Test FRED series ID mapping."""
    
    def test_series_ids_defined(self):
        """Test all required series IDs are defined."""
        from src.tools.fred_data import FRED_SERIES
        
        required = ["DXY", "TREASURY_10Y", "CPI", "PCE", "FED_FUNDS"]
        
        for key in required:
            assert key in FRED_SERIES
            assert isinstance(FRED_SERIES[key], str)
            assert len(FRED_SERIES[key]) > 0
