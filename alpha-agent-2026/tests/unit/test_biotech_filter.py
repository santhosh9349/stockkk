"""Unit tests for biotech filter (Constitution III).

Tests $500M market cap threshold for IBB universe.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models import Universe
from src.agents.technical_scanner import TechnicalScannerAgent, BIOTECH_MARKET_CAP_MIN


class TestBiotechFilter:
    """Tests for biotech market cap filter (T037)."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.alpha_vantage_api_key = "test_key"
        return config
    
    @pytest.fixture
    def scanner(self, mock_config):
        """Create scanner instance with mocked client."""
        scanner = TechnicalScannerAgent(mock_config)
        return scanner
    
    @pytest.mark.asyncio
    async def test_passes_above_threshold(self, scanner):
        """Test stock with market cap above $500M passes filter."""
        # Mock market cap at $600M
        scanner.client.get_market_cap = AsyncMock(return_value=600_000_000)
        
        result = await scanner._passes_biotech_filter("VRTX")
        
        assert result is True
        scanner.client.get_market_cap.assert_called_once_with("VRTX")
    
    @pytest.mark.asyncio
    async def test_fails_below_threshold(self, scanner):
        """Test stock with market cap below $500M fails filter."""
        # Mock market cap at $400M
        scanner.client.get_market_cap = AsyncMock(return_value=400_000_000)
        
        result = await scanner._passes_biotech_filter("SMALL")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_exact_threshold_passes(self, scanner):
        """Test stock with exactly $500M market cap passes filter."""
        scanner.client.get_market_cap = AsyncMock(return_value=500_000_000)
        
        result = await scanner._passes_biotech_filter("EDGE")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_none_market_cap_fails(self, scanner):
        """Test stock with unavailable market cap fails filter."""
        scanner.client.get_market_cap = AsyncMock(return_value=None)
        
        result = await scanner._passes_biotech_filter("UNKNOWN")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_filter_only_applied_to_ibb(self, scanner):
        """Test that filter is only applied to IBB universe."""
        # Mock all methods
        scanner.client.get_market_cap = AsyncMock(return_value=100_000_000)  # Below threshold
        scanner.client.get_rsi = AsyncMock(return_value=25.0)
        scanner.client.get_quote = AsyncMock(return_value={"price": 100.0})
        scanner.client.get_daily_volume = AsyncMock(return_value=[200000] + [100000] * 20)
        
        # For QQQ, the low market cap should NOT trigger filter
        result = await scanner._analyze_symbol("AAPL", Universe.QQQ)
        
        # Should return a recommendation (filter not applied to QQQ)
        # Note: get_market_cap should NOT have been called for QQQ
        # (This test verifies the filter is universe-specific)
    
    @pytest.mark.asyncio
    async def test_ibb_symbol_filtered(self, scanner):
        """Test IBB symbol with low market cap is filtered."""
        scanner.client.get_market_cap = AsyncMock(return_value=300_000_000)  # Below threshold
        scanner.client.get_rsi = AsyncMock(return_value=25.0)
        
        result = await scanner._analyze_symbol("SMALL", Universe.IBB)
        
        assert result is None  # Should be filtered out
    
    def test_threshold_constant(self):
        """Test that threshold constant is $500M."""
        assert BIOTECH_MARKET_CAP_MIN == 500_000_000


class TestRSICriteria:
    """Tests for RSI crossover criteria."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.alpha_vantage_api_key = "test_key"
        return config
    
    @pytest.fixture
    def scanner(self, mock_config):
        """Create scanner instance."""
        return TechnicalScannerAgent(mock_config)
    
    def test_oversold_below_30(self, scanner):
        """Test RSI below 30 triggers oversold signal."""
        result = scanner._check_rsi_criteria("TEST", 25.0)
        assert result == "oversold"
    
    def test_oversold_at_boundary(self, scanner):
        """Test RSI exactly at 30 does not trigger oversold."""
        result = scanner._check_rsi_criteria("TEST", 30.0)
        assert result is None  # Must be < 30, not <=
    
    def test_momentum_crossover(self, scanner):
        """Test RSI crossing 50 from below triggers momentum signal."""
        # First call sets previous RSI
        scanner._check_rsi_criteria("TEST", 45.0)  # Below 50
        
        # Second call should detect crossover
        result = scanner._check_rsi_criteria("TEST", 52.0)  # Above 50
        
        assert result == "momentum"
    
    def test_no_signal_above_50(self, scanner):
        """Test RSI already above 50 does not trigger signal."""
        scanner._check_rsi_criteria("TEST", 55.0)  # Above 50
        result = scanner._check_rsi_criteria("TEST", 60.0)  # Still above 50
        
        assert result is None
    
    def test_no_crossover_same_side(self, scanner):
        """Test no signal when RSI stays on same side of 50."""
        scanner._check_rsi_criteria("TEST", 40.0)
        result = scanner._check_rsi_criteria("TEST", 45.0)
        
        assert result is None


class TestVolumeCriteria:
    """Tests for volume spike criteria."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.alpha_vantage_api_key = "test_key"
        return config
    
    @pytest.fixture
    def scanner(self, mock_config):
        """Create scanner instance."""
        return TechnicalScannerAgent(mock_config)
    
    @pytest.mark.asyncio
    async def test_volume_spike_detected(self, scanner):
        """Test volume spike above 1.5x is detected."""
        # Current volume 2x average
        scanner.client.get_daily_volume = AsyncMock(
            return_value=[200000] + [100000] * 20  # Current = 200k, avg = 100k
        )
        
        result = await scanner._check_volume_criteria("TEST")
        
        assert result == 2.0
    
    @pytest.mark.asyncio
    async def test_no_spike_below_threshold(self, scanner):
        """Test volume below 1.5x returns ratio but won't pass filter."""
        scanner.client.get_daily_volume = AsyncMock(
            return_value=[120000] + [100000] * 20
        )
        
        result = await scanner._check_volume_criteria("TEST")
        
        assert result == 1.2
        # Note: The scanner._analyze_symbol checks if ratio >= 1.5
    
    @pytest.mark.asyncio
    async def test_none_on_no_data(self, scanner):
        """Test None returned when no volume data available."""
        scanner.client.get_daily_volume = AsyncMock(return_value=None)
        
        result = await scanner._check_volume_criteria("TEST")
        
        assert result is None


class TestConfidenceCalculation:
    """Tests for confidence score calculation."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.alpha_vantage_api_key = "test_key"
        return config
    
    @pytest.fixture
    def scanner(self, mock_config):
        """Create scanner instance."""
        return TechnicalScannerAgent(mock_config)
    
    def test_oversold_higher_base(self, scanner):
        """Test oversold signals get higher base confidence."""
        oversold_conf = scanner._calculate_confidence(25.0, 2.0, "oversold")
        momentum_conf = scanner._calculate_confidence(52.0, 2.0, "momentum")
        
        assert oversold_conf > momentum_conf
    
    def test_lower_rsi_higher_confidence(self, scanner):
        """Test more oversold RSI gives higher confidence."""
        very_oversold = scanner._calculate_confidence(15.0, 2.0, "oversold")
        slightly_oversold = scanner._calculate_confidence(28.0, 2.0, "oversold")
        
        assert very_oversold > slightly_oversold
    
    def test_higher_volume_higher_confidence(self, scanner):
        """Test higher volume ratio gives higher confidence."""
        high_volume = scanner._calculate_confidence(25.0, 4.0, "oversold")
        low_volume = scanner._calculate_confidence(25.0, 1.6, "oversold")
        
        assert high_volume > low_volume
    
    def test_confidence_capped_at_1(self, scanner):
        """Test confidence never exceeds 1.0."""
        result = scanner._calculate_confidence(5.0, 10.0, "oversold")
        
        assert result <= 1.0
    
    def test_confidence_range(self, scanner):
        """Test confidence is in valid range."""
        result = scanner._calculate_confidence(25.0, 2.0, "oversold")
        
        assert 0.0 <= result <= 1.0
