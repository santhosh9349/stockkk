"""Shared pytest fixtures for Alpha-Agent 2026 tests."""

import pytest
from datetime import date, datetime
from typing import Generator
from unittest.mock import MagicMock, AsyncMock

# Import models when they exist
# from src.models import TradeRecommendation, PortfolioHolding, IntelligenceReport


@pytest.fixture
def mock_config() -> dict:
    """Mock configuration for testing."""
    return {
        "ALPHA_VANTAGE_API_KEY": "test_av_key",
        "FRED_API_KEY": "test_fred_key",
        "TELEGRAM_BOT_TOKEN": "test_bot_token",
        "TELEGRAM_CHAT_ID": "123456789",
        "GITHUB_TOKEN": "test_gh_token",
        "GITHUB_REPOSITORY": "test/repo",
        "LOG_LEVEL": "DEBUG",
        "PIPELINE_TIMEOUT_MINUTES": "25",
    }


@pytest.fixture
def sample_portfolio_data() -> dict:
    """Sample portfolio data for testing."""
    return {
        "holdings": [
            {
                "symbol": "AAPL",
                "shares": 100,
                "cost_basis": 150.00,
                "entry_date": "2025-06-15",
            },
            {
                "symbol": "NVDA",
                "shares": 50,
                "cost_basis": 450.00,
                "entry_date": "2025-08-01",
            },
            {
                "symbol": "MRNA",
                "shares": 25,
                "cost_basis": 120.00,
                "entry_date": "2025-09-10",
            },
        ],
        "last_updated": "2026-01-14T08:00:00Z",
    }


@pytest.fixture
def sample_trade_recommendation() -> dict:
    """Sample trade recommendation data conforming to Constitution I."""
    return {
        "symbol": "TSLA",
        "universe": "QQQ",
        "entry": 250.00,
        "target": 275.00,
        "stop_loss": 243.75,  # 2.5% below entry (250 * 0.975)
        "rsi": 32.5,
        "volume_ratio": 1.8,
        "confidence": 0.85,
        "market_cap": 800_000_000_000,
    }


@pytest.fixture
def sample_biotech_under_cap() -> dict:
    """Sample biotech stock under $500M cap (should be excluded)."""
    return {
        "symbol": "TINY",
        "universe": "IBB",
        "entry": 15.00,
        "target": 18.00,
        "stop_loss": 14.625,
        "rsi": 28.0,
        "volume_ratio": 2.1,
        "confidence": 0.72,
        "market_cap": 350_000_000,  # Below $500M threshold
    }


@pytest.fixture
def sample_macro_indicators() -> list[dict]:
    """Sample macro indicator data."""
    return [
        {
            "name": "DXY",
            "value": 104.25,
            "previous_value": 103.80,
            "trend": "STRENGTHENING",
            "source": "FRED",
        },
        {
            "name": "TREASURY_10Y",
            "value": 4.35,
            "previous_value": 4.28,
            "trend": "STRENGTHENING",
            "source": "FRED",
        },
        {
            "name": "CPI",
            "value": 3.1,
            "previous_value": 3.2,
            "trend": "WEAKENING",
            "source": "FRED",
        },
    ]


@pytest.fixture
def mock_alpha_vantage_client() -> MagicMock:
    """Mock Alpha Vantage API client."""
    client = MagicMock()
    client.get_quote = AsyncMock(return_value={"price": 150.00, "volume": 1_000_000})
    client.get_rsi = AsyncMock(return_value=45.0)
    client.get_sma = AsyncMock(return_value=148.50)
    client.get_market_cap = AsyncMock(return_value=2_500_000_000_000)
    return client


@pytest.fixture
def mock_fred_client() -> MagicMock:
    """Mock FRED API client."""
    client = MagicMock()
    client.get_dxy = AsyncMock(return_value=104.25)
    client.get_treasury_10y = AsyncMock(return_value=4.35)
    client.get_cpi = AsyncMock(return_value=3.1)
    client.get_pce = AsyncMock(return_value=2.8)
    return client


@pytest.fixture
def mock_telegram_bot() -> MagicMock:
    """Mock Telegram bot for notification testing."""
    bot = MagicMock()
    bot.send_message = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def nyse_holidays_2026() -> list[str]:
    """NYSE holidays for 2026."""
    return [
        "2026-01-01",  # New Year's Day
        "2026-01-19",  # Martin Luther King Jr. Day
        "2026-02-16",  # Presidents Day
        "2026-04-03",  # Good Friday
        "2026-05-25",  # Memorial Day
        "2026-07-03",  # Independence Day (observed)
        "2026-09-07",  # Labor Day
        "2026-11-26",  # Thanksgiving
        "2026-12-25",  # Christmas
    ]


@pytest.fixture
def current_trading_day() -> date:
    """Return a known trading day for consistent testing."""
    return date(2026, 1, 15)  # Wednesday, January 15, 2026
