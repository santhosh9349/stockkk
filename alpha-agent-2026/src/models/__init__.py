"""Pydantic data models and enumerations for Alpha-Agent 2026.

This module defines all entity types used across the investment intelligence system.
All models enforce Constitution compliance through validation rules.
"""

from enum import Enum


class Universe(str, Enum):
    """Stock universe for scanning (FR-004)."""
    QQQ = "QQQ"      # NASDAQ 100
    IBB = "IBB"      # Biotech (Constitution III: $500M floor)
    ITA = "ITA"      # Aerospace/Defense
    SPY = "SPY"      # S&P 500


class Signal(str, Enum):
    """Portfolio holding signals (Constitution III)."""
    EXIT = "EXIT"       # -5% SMA AND (position > 10% OR loss > 10%)
    HEDGE = "HEDGE"     # -5% SMA AND smaller position
    TOP_UP = "TOP_UP"   # Positive momentum + favorable sentiment
    HOLD = "HOLD"       # Default state


class EventType(str, Enum):
    """Catalyst event types (FR-014)."""
    EARNINGS = "EARNINGS"
    PDUFA = "PDUFA"               # FDA drug approval dates
    FED_SPEAKER = "FED_SPEAKER"
    FED = "FED"                   # Federal Reserve announcements
    ECONOMIC_RELEASE = "ECONOMIC_RELEASE"
    ECONOMIC = "ECONOMIC"         # Economic data releases
    CYCLICAL = "CYCLICAL"


class TimeBucket(str, Enum):
    """Event time categorization (FR-014)."""
    TODAY = "TODAY"
    THIS_WEEK = "THIS_WEEK"
    THREE_MONTH = "THREE_MONTH"
    BEYOND = "BEYOND"
    PAST = "PAST"


class Trend(str, Enum):
    """Directional trend indicator."""
    STRENGTHENING = "STRENGTHENING"
    WEAKENING = "WEAKENING"
    NEUTRAL = "NEUTRAL"
    STABLE = "STABLE"


class ReportStatus(str, Enum):
    """Report generation status (FR-026, FR-027)."""
    COMPLETE = "COMPLETE"           # All sections populated
    PARTIAL = "PARTIAL"             # Some data unavailable
    MARKET_CLOSED = "MARKET_CLOSED" # Holiday mode


class MetalsAction(str, Enum):
    """Metals advisor recommendations (Constitution IV)."""
    ACCUMULATE = "ACCUMULATE"     # DXY strengthening
    PROFIT_TAKE = "PROFIT_TAKE"   # Overbought + geopolitical tension
    HOLD = "HOLD"                 # Default state


# Export all enums
__all__ = [
    "Universe",
    "Signal",
    "EventType",
    "TimeBucket",
    "Trend",
    "ReportStatus",
    "MetalsAction",
]
