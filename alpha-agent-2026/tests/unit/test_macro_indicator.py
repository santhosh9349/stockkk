"""Unit tests for MacroIndicator model and trend calculation."""

import pytest
from datetime import date

from src.models.macro_indicator import (
    MacroIndicator,
    Trend,
    calculate_trend,
    create_dxy_indicator,
    create_treasury_indicator,
    create_cpi_indicator,
)


class TestTrendCalculation:
    """Test trend calculation logic."""
    
    def test_strengthening_trend(self):
        """Test trend calculation for increasing values."""
        current = 105.0
        previous = 100.0
        
        trend = calculate_trend(current, previous)
        
        assert trend == Trend.STRENGTHENING
    
    def test_weakening_trend(self):
        """Test trend calculation for decreasing values."""
        current = 95.0
        previous = 100.0
        
        trend = calculate_trend(current, previous)
        
        assert trend == Trend.WEAKENING
    
    def test_stable_trend(self):
        """Test trend calculation for stable values (within threshold)."""
        current = 100.5
        previous = 100.0
        
        # Default threshold is 0.5%
        trend = calculate_trend(current, previous, threshold=0.01)
        
        assert trend == Trend.STABLE
    
    def test_zero_previous_value(self):
        """Test trend calculation with zero previous value."""
        current = 100.0
        previous = 0.0
        
        # Should handle gracefully
        trend = calculate_trend(current, previous)
        
        assert trend in [Trend.STRENGTHENING, Trend.STABLE]
    
    def test_negative_change(self):
        """Test negative percentage change."""
        current = 90.0
        previous = 100.0
        
        trend = calculate_trend(current, previous)
        
        assert trend == Trend.WEAKENING


class TestMacroIndicatorModel:
    """Test MacroIndicator Pydantic model."""
    
    def test_create_macro_indicator(self):
        """Test creating a macro indicator."""
        indicator = MacroIndicator(
            name="DXY",
            current_value=104.25,
            previous_value=103.50,
            trend=Trend.STRENGTHENING,
            as_of_date=date.today(),
        )
        
        assert indicator.name == "DXY"
        assert indicator.current_value == 104.25
        assert indicator.trend == Trend.STRENGTHENING
    
    def test_macro_indicator_change_percent(self):
        """Test change percentage calculation."""
        indicator = MacroIndicator(
            name="Treasury 10Y",
            current_value=4.50,
            previous_value=4.25,
            trend=Trend.STRENGTHENING,
            as_of_date=date.today(),
        )
        
        # ~5.88% increase
        expected_change = ((4.50 - 4.25) / 4.25) * 100
        
        assert indicator.change_pct == pytest.approx(expected_change, rel=0.01)
    
    def test_macro_indicator_serialization(self):
        """Test macro indicator JSON serialization."""
        indicator = MacroIndicator(
            name="CPI",
            current_value=3.2,
            previous_value=3.4,
            trend=Trend.WEAKENING,
            as_of_date=date.today(),
        )
        
        data = indicator.model_dump()
        
        assert data["name"] == "CPI"
        assert data["current_value"] == 3.2
        assert data["trend"] == "WEAKENING"


class TestDXYIndicator:
    """Test DXY indicator factory."""
    
    def test_create_dxy_strengthening(self):
        """Test DXY indicator with strengthening dollar."""
        indicator = create_dxy_indicator(
            current=106.0,
            previous=103.0,
        )
        
        assert indicator.name == "DXY"
        assert indicator.trend == Trend.STRENGTHENING
    
    def test_create_dxy_weakening(self):
        """Test DXY indicator with weakening dollar."""
        indicator = create_dxy_indicator(
            current=98.0,
            previous=102.0,
        )
        
        assert indicator.name == "DXY"
        assert indicator.trend == Trend.WEAKENING


class TestTreasuryIndicator:
    """Test Treasury indicator factory."""
    
    def test_create_treasury_rising(self):
        """Test Treasury indicator with rising yields."""
        indicator = create_treasury_indicator(
            current=4.75,
            previous=4.25,
        )
        
        assert indicator.name == "Treasury 10Y"
        assert indicator.trend == Trend.STRENGTHENING
    
    def test_create_treasury_falling(self):
        """Test Treasury indicator with falling yields."""
        indicator = create_treasury_indicator(
            current=4.00,
            previous=4.50,
        )
        
        assert indicator.name == "Treasury 10Y"
        assert indicator.trend == Trend.WEAKENING


class TestCPIIndicator:
    """Test CPI indicator factory."""
    
    def test_create_cpi_rising(self):
        """Test CPI indicator with rising inflation."""
        indicator = create_cpi_indicator(
            current=3.8,
            previous=3.2,
        )
        
        assert indicator.name == "CPI"
        assert indicator.trend == Trend.STRENGTHENING
    
    def test_create_cpi_falling(self):
        """Test CPI indicator with falling inflation."""
        indicator = create_cpi_indicator(
            current=2.8,
            previous=3.5,
        )
        
        assert indicator.name == "CPI"
        assert indicator.trend == Trend.WEAKENING


class TestMacroIndicatorDisplay:
    """Test macro indicator display formatting."""
    
    def test_indicator_display_string(self):
        """Test display string formatting."""
        indicator = MacroIndicator(
            name="DXY",
            current_value=104.25,
            previous_value=103.50,
            trend=Trend.STRENGTHENING,
            as_of_date=date(2026, 1, 15),
        )
        
        display = indicator.display_string()
        
        assert "DXY" in display
        assert "104.25" in display or "104.2" in display
        assert "↑" in display or "STRENGTHENING" in display or "strengthening" in display.lower()
