"""Portfolio reader tool for loading and validating portfolio data.

Implements FR-029: Portfolio JSON schema validation with stale data detection.
Read-only access per Constitution II (Data Governance).
"""

import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator, model_validator

from src.utils.logging import get_logger

logger = get_logger(__name__)


class PortfolioHoldingSchema(BaseModel):
    """Schema for a single portfolio holding (FR-029)."""
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    shares: float = Field(..., gt=0, description="Number of shares held")
    avg_cost: float = Field(..., gt=0, description="Average cost basis per share")
    sector: Optional[str] = Field(None, description="Market sector classification")
    acquired_date: Optional[str] = Field(None, description="Date position was acquired (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, description="Optional notes about the position")
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        return v.upper().strip()
    
    @field_validator("acquired_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format if provided."""
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format: {v}. Expected YYYY-MM-DD")
        return v


class PortfolioSchema(BaseModel):
    """Schema for the full portfolio JSON file (FR-029)."""
    
    last_updated: str = Field(..., description="Last update timestamp (ISO format)")
    holdings: list[PortfolioHoldingSchema] = Field(..., min_length=1, description="List of holdings")
    metadata: Optional[dict[str, Any]] = Field(None, description="Optional metadata")
    
    @field_validator("last_updated")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is parseable."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}. Expected ISO format")
        return v
    
    @model_validator(mode="after")
    def validate_no_duplicate_symbols(self) -> "PortfolioSchema":
        """Ensure no duplicate symbols in holdings."""
        symbols = [h.symbol for h in self.holdings]
        duplicates = [s for s in symbols if symbols.count(s) > 1]
        if duplicates:
            raise ValueError(f"Duplicate symbols found: {set(duplicates)}")
        return self


@dataclass
class ValidationResult:
    """Result of portfolio validation."""
    
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    portfolio: Optional[PortfolioSchema] = None
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0


class PortfolioReader:
    """Portfolio reader with validation and stale data detection (FR-029).
    
    Provides read-only access to portfolio data per Constitution II.
    """
    
    # Stale data threshold (portfolio not updated in 24 hours)
    STALE_THRESHOLD_HOURS = 24
    
    def __init__(self, portfolio_path: str | Path):
        """Initialize reader with portfolio file path.
        
        Args:
            portfolio_path: Path to portfolio.json file
        """
        self.portfolio_path = Path(portfolio_path)
        self._cached_portfolio: Optional[PortfolioSchema] = None
        self._cache_time: Optional[datetime] = None
    
    def _check_file_exists(self) -> bool:
        """Check if portfolio file exists."""
        return self.portfolio_path.exists()
    
    def _load_raw_json(self) -> dict[str, Any]:
        """Load raw JSON from file.
        
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        if not self._check_file_exists():
            raise FileNotFoundError(f"Portfolio file not found: {self.portfolio_path}")
        
        with open(self.portfolio_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _check_stale_data(self, last_updated: str) -> Optional[str]:
        """Check if portfolio data is stale (FR-029).
        
        Args:
            last_updated: ISO timestamp of last update
            
        Returns:
            Warning message if stale, None otherwise
        """
        try:
            update_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            # Convert to naive datetime for comparison if needed
            if update_time.tzinfo is not None:
                update_time = update_time.replace(tzinfo=None)
            
            age = datetime.now() - update_time
            
            if age > timedelta(hours=self.STALE_THRESHOLD_HOURS):
                hours_old = age.total_seconds() / 3600
                return f"Portfolio data is stale ({hours_old:.1f} hours old). Last updated: {last_updated}"
            
            return None
            
        except Exception as e:
            return f"Unable to determine data age: {e}"
    
    def validate(self) -> ValidationResult:
        """Validate portfolio JSON against schema (FR-029).
        
        Performs:
        1. File existence check
        2. JSON syntax validation
        3. Schema validation (required fields, types)
        4. Stale data detection
        5. Business rule validation (no duplicates, positive values)
        
        Returns:
            ValidationResult with status, errors, and warnings
        """
        errors: list[str] = []
        warnings: list[str] = []
        portfolio: Optional[PortfolioSchema] = None
        
        # Step 1: File existence
        if not self._check_file_exists():
            return ValidationResult(
                is_valid=False,
                errors=[f"Portfolio file not found: {self.portfolio_path}"],
                warnings=[],
            )
        
        # Step 2: JSON syntax
        try:
            raw_data = self._load_raw_json()
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid JSON syntax: {e}"],
                warnings=[],
            )
        
        # Step 3: Schema validation
        try:
            portfolio = PortfolioSchema(**raw_data)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Schema validation failed: {e}"],
                warnings=[],
            )
        
        # Step 4: Stale data check
        stale_warning = self._check_stale_data(portfolio.last_updated)
        if stale_warning:
            warnings.append(stale_warning)
            logger.warning(stale_warning)
        
        # Step 5: Business rule validation (already done by Pydantic)
        # Additional checks can be added here
        
        # Check for very small positions (< $100 value)
        for holding in portfolio.holdings:
            position_value = holding.shares * holding.avg_cost
            if position_value < 100:
                warnings.append(
                    f"Very small position: {holding.symbol} (${position_value:.2f})"
                )
        
        return ValidationResult(
            is_valid=True,
            errors=errors,
            warnings=warnings,
            portfolio=portfolio,
        )
    
    def load(self) -> PortfolioSchema:
        """Load and validate portfolio data.
        
        Caches the result for subsequent calls.
        
        Returns:
            Validated portfolio data
            
        Raises:
            ValueError: If portfolio validation fails
        """
        # Return cached if recent (1 minute)
        if self._cached_portfolio and self._cache_time:
            if datetime.now() - self._cache_time < timedelta(minutes=1):
                return self._cached_portfolio
        
        result = self.validate()
        
        if not result.is_valid:
            error_msg = "; ".join(result.errors)
            raise ValueError(f"Portfolio validation failed: {error_msg}")
        
        if result.warnings:
            for warning in result.warnings:
                logger.warning(warning)
        
        self._cached_portfolio = result.portfolio
        self._cache_time = datetime.now()
        
        return result.portfolio  # type: ignore
    
    def get_holdings(self) -> list[PortfolioHoldingSchema]:
        """Get list of portfolio holdings.
        
        Returns:
            List of validated holdings
        """
        portfolio = self.load()
        return portfolio.holdings
    
    def get_holding(self, symbol: str) -> Optional[PortfolioHoldingSchema]:
        """Get a specific holding by symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Holding if found, None otherwise
        """
        symbol = symbol.upper().strip()
        holdings = self.get_holdings()
        
        for holding in holdings:
            if holding.symbol == symbol:
                return holding
        
        return None
    
    def get_symbols(self) -> list[str]:
        """Get list of all symbols in portfolio.
        
        Returns:
            List of ticker symbols
        """
        holdings = self.get_holdings()
        return [h.symbol for h in holdings]
    
    def get_total_value(self, current_prices: Optional[dict[str, float]] = None) -> float:
        """Calculate total portfolio value.
        
        Args:
            current_prices: Optional dict of current prices by symbol.
                           Uses avg_cost if not provided.
        
        Returns:
            Total portfolio value
        """
        holdings = self.get_holdings()
        total = 0.0
        
        for holding in holdings:
            if current_prices and holding.symbol in current_prices:
                price = current_prices[holding.symbol]
            else:
                price = holding.avg_cost
            
            total += holding.shares * price
        
        return total
    
    def get_position_weights(
        self, current_prices: Optional[dict[str, float]] = None
    ) -> dict[str, float]:
        """Calculate position weights as percentage of portfolio.
        
        Args:
            current_prices: Optional dict of current prices by symbol.
        
        Returns:
            Dict mapping symbol to weight (0-100)
        """
        holdings = self.get_holdings()
        total = self.get_total_value(current_prices)
        
        if total == 0:
            return {h.symbol: 0.0 for h in holdings}
        
        weights = {}
        for holding in holdings:
            if current_prices and holding.symbol in current_prices:
                price = current_prices[holding.symbol]
            else:
                price = holding.avg_cost
            
            position_value = holding.shares * price
            weights[holding.symbol] = (position_value / total) * 100
        
        return weights


def load_portfolio(path: str | Path) -> PortfolioSchema:
    """Convenience function to load and validate portfolio.
    
    Args:
        path: Path to portfolio.json file
        
    Returns:
        Validated portfolio data
        
    Raises:
        ValueError: If validation fails
    """
    reader = PortfolioReader(path)
    return reader.load()
