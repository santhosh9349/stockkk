"""Intelligence Report model for Alpha-Agent 2026.

Defines the daily consolidated report structure with status tracking
for partial report handling per FR-026.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from . import ReportStatus


class DataUnavailable:
    """Sentinel class for marking unavailable data sections.
    
    Used when a data source fails after all retry attempts (FR-026).
    Allows the report to proceed with partial data.
    """
    
    def __init__(self, source: str, error: str | None = None):
        """Initialize unavailable data marker.
        
        Args:
            source: Name of the data source that failed
            error: Optional error message
        """
        self.source = source
        self.error = error
        self.timestamp = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"DataUnavailable(source='{self.source}', error='{self.error}')"
    
    def to_markdown(self) -> str:
        """Format for inclusion in Markdown report."""
        return f"⚠️ **Data Unavailable**: {self.source}\n> {self.error or 'Unknown error'}"


class IntelligenceReport(BaseModel):
    """The daily consolidated intelligence report.
    
    Contains outputs from all agents with status tracking for partial reports.
    Implements FR-026 partial report handling.
    """
    
    # Report metadata
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    status: ReportStatus = ReportStatus.COMPLETE
    
    # Agent outputs (will be properly typed when models are created)
    technical_scans: list[Any] = Field(
        default_factory=list,
        description="Top 10 breakout candidates (FR-009)"
    )
    portfolio_alerts: list[Any] = Field(
        default_factory=list,
        description="Holdings with Exit/Hedge/Top-up signals"
    )
    catalysts: list[Any] = Field(
        default_factory=list,
        description="Upcoming market events by time bucket"
    )
    macro_indicators: list[Any] = Field(
        default_factory=list,
        description="Current macro readings (DXY, Treasury, CPI, PCE)"
    )
    metals_advice: Any | None = Field(
        default=None,
        description="Gold/Silver timing recommendation"
    )
    
    # Data availability tracking (FR-026)
    unavailable_sections: list[str] = Field(
        default_factory=list,
        description="Sections that failed to load after retries"
    )
    
    # Market status
    market_holiday: bool = Field(
        default=False,
        description="True if market is closed (FR-027)"
    )
    holiday_name: str | None = Field(
        default=None,
        description="Name of holiday if market closed"
    )
    
    def mark_unavailable(self, section: str, error: str | None = None) -> None:
        """Mark a section as unavailable (FR-026).
        
        Args:
            section: Name of the section that failed
            error: Optional error message
        """
        if section not in self.unavailable_sections:
            self.unavailable_sections.append(section)
        self.status = ReportStatus.PARTIAL
    
    def mark_market_closed(self, holiday_name: str | None = None) -> None:
        """Mark report as market closed (FR-027).
        
        Args:
            holiday_name: Optional name of the holiday
        """
        self.status = ReportStatus.MARKET_CLOSED
        self.market_holiday = True
        self.holiday_name = holiday_name
    
    @property
    def is_complete(self) -> bool:
        """Check if all sections have data."""
        return self.status == ReportStatus.COMPLETE
    
    @property
    def is_partial(self) -> bool:
        """Check if some sections are unavailable."""
        return self.status == ReportStatus.PARTIAL
    
    @property
    def is_market_closed(self) -> bool:
        """Check if market is closed."""
        return self.status == ReportStatus.MARKET_CLOSED
    
    def get_summary_stats(self) -> dict[str, int]:
        """Get summary statistics for the report."""
        return {
            "technical_scans": len(self.technical_scans),
            "portfolio_alerts": len(self.portfolio_alerts),
            "catalysts": len(self.catalysts),
            "macro_indicators": len(self.macro_indicators),
            "has_metals_advice": 1 if self.metals_advice else 0,
            "unavailable_sections": len(self.unavailable_sections),
        }
