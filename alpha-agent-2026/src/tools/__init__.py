"""MCP-compliant financial data tools package.

Tools in this package provide read-only access to financial data
per Constitution II (Data Governance).

Available tools:
- AlphaVantageClient: Technical indicators, quotes, market cap
- PortfolioReader: Portfolio JSON loading and validation
"""

from src.tools.alpha_vantage import (
    AlphaVantageClient,
    StockStatus,
    StockStatusResult,
    filter_tradeable_symbols,
)
from src.tools.portfolio_reader import (
    PortfolioReader,
    PortfolioSchema,
    PortfolioHoldingSchema,
    ValidationResult,
    load_portfolio,
)

__all__ = [
    # Alpha Vantage
    "AlphaVantageClient",
    "StockStatus",
    "StockStatusResult",
    "filter_tradeable_symbols",
    # Portfolio
    "PortfolioReader",
    "PortfolioSchema",
    "PortfolioHoldingSchema",
    "ValidationResult",
    "load_portfolio",
]
