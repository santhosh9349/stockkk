# Data Model: Multi-Agent Investment Ecosystem

**Feature**: 1-multi-agent-investment  
**Date**: 2026-01-14  
**Purpose**: Define entity schemas, relationships, and validation rules

---

## Entity Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────┐
│  IntelligenceReport │       │   PortfolioHolding  │
│─────────────────────│       │─────────────────────│
│  id: UUID           │       │  symbol: str        │
│  timestamp: datetime│       │  shares: float      │
│  status: ReportStatus       │  cost_basis: float  │
│─────────────────────│       │  entry_date: date   │
│  technical_scans: []│──┐    │  signal: Signal     │
│  portfolio_alerts:[]│──┼────│  rationale: str     │
│  catalysts: []      │──┤    └─────────────────────┘
│  macro_indicators:[]│──┤
│  metals_advice: obj │──┤    ┌─────────────────────┐
└─────────────────────┘  │    │ TradeRecommendation │
                         │    │─────────────────────│
                         ├───→│  symbol: str        │
                         │    │  entry: float       │ ← REQUIRED (Constitution I)
                         │    │  target: float      │ ← REQUIRED (Constitution I)
                         │    │  stop_loss: float   │ ← REQUIRED (2.5% trailing)
                         │    │  rsi: float         │
                         │    │  volume_ratio: float│
                         │    │  confidence: float  │
                         │    │  universe: Universe │
                         │    └─────────────────────┘
                         │
                         │    ┌─────────────────────┐
                         ├───→│   CatalystEvent     │
                         │    │─────────────────────│
                         │    │  date: date         │
                         │    │  type: EventType    │
                         │    │  symbols: [str]     │
                         │    │  time_bucket: Bucket│
                         │    │  impact: str        │
                         │    └─────────────────────┘
                         │
                         │    ┌─────────────────────┐
                         └───→│   MacroIndicator    │
                              │─────────────────────│
                              │  name: str          │
                              │  value: float       │
                              │  trend: Trend       │
                              │  updated_at: datetime
                              └─────────────────────┘
```

---

## Enumerations

```python
from enum import Enum

class Universe(str, Enum):
    """Stock universe for scanning"""
    QQQ = "QQQ"      # NASDAQ 100
    IBB = "IBB"      # Biotech
    ITA = "ITA"      # Aerospace/Defense
    SPY = "SPY"      # S&P 500

class Signal(str, Enum):
    """Portfolio holding signals"""
    EXIT = "EXIT"
    HEDGE = "HEDGE"
    TOP_UP = "TOP_UP"
    HOLD = "HOLD"

class EventType(str, Enum):
    """Catalyst event types"""
    EARNINGS = "EARNINGS"
    PDUFA = "PDUFA"           # FDA drug approval dates
    FED_SPEAKER = "FED_SPEAKER"
    ECONOMIC_RELEASE = "ECONOMIC_RELEASE"
    CYCLICAL = "CYCLICAL"

class TimeBucket(str, Enum):
    """Event time categorization"""
    TODAY = "TODAY"
    THIS_WEEK = "THIS_WEEK"
    THREE_MONTH = "THREE_MONTH"

class Trend(str, Enum):
    """Directional trend"""
    STRENGTHENING = "STRENGTHENING"
    WEAKENING = "WEAKENING"
    NEUTRAL = "NEUTRAL"

class ReportStatus(str, Enum):
    """Report generation status"""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"        # Some data unavailable
    MARKET_CLOSED = "MARKET_CLOSED"

class MetalsAction(str, Enum):
    """Metals advisor recommendations"""
    ACCUMULATE = "ACCUMULATE"
    PROFIT_TAKE = "PROFIT_TAKE"
    HOLD = "HOLD"
```

---

## Entity Schemas

### TradeRecommendation

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class TradeRecommendation(BaseModel):
    """
    A potential trade opportunity.
    Constitution I: Entry, Target, and Stop-Loss are ALL required.
    """
    symbol: str = Field(..., min_length=1, max_length=10)
    universe: Universe
    
    # Constitution I - REQUIRED fields (non-nullable)
    entry: float = Field(..., gt=0, description="Entry price")
    target: float = Field(..., gt=0, description="Target price")
    stop_loss: float = Field(..., gt=0, description="2.5% trailing stop-loss")
    
    # Technical indicators
    rsi: float = Field(..., ge=0, le=100)
    volume_ratio: float = Field(..., gt=0, description="Volume vs 20-day avg")
    
    # Metadata
    confidence: float = Field(..., ge=0, le=1, description="Signal strength 0-1")
    market_cap: float | None = Field(None, description="Market cap in USD")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('stop_loss')
    @classmethod
    def validate_stop_loss(cls, v, info):
        """Ensure stop_loss is exactly 2.5% below entry"""
        entry = info.data.get('entry')
        if entry and abs(v - (entry * 0.975)) > 0.01:
            raise ValueError('Stop-loss must be 2.5% below entry price')
        return v
    
    @field_validator('target')
    @classmethod
    def validate_target_above_entry(cls, v, info):
        """Target must be above entry for long recommendations"""
        entry = info.data.get('entry')
        if entry and v <= entry:
            raise ValueError('Target must be above entry price')
        return v
```

### PortfolioHolding

```python
class PortfolioHolding(BaseModel):
    """
    A current portfolio position with health analysis.
    """
    symbol: str = Field(..., min_length=1, max_length=10)
    shares: float = Field(..., gt=0)
    cost_basis: float = Field(..., gt=0, description="Average cost per share")
    entry_date: date
    
    # Computed at analysis time
    current_price: float | None = None
    sma_20: float | None = None
    pct_vs_sma: float | None = Field(None, description="% deviation from 20-day SMA")
    position_pct: float | None = Field(None, description="% of total portfolio")
    pnl_pct: float | None = Field(None, description="Unrealized P&L %")
    sentiment_score: float | None = Field(None, ge=-1, le=1)
    
    # Signal output
    signal: Signal | None = None
    rationale: str | None = None
    
    @property
    def value(self) -> float | None:
        """Current position value"""
        if self.current_price:
            return self.shares * self.current_price
        return None
```

### CatalystEvent

```python
class CatalystEvent(BaseModel):
    """
    A market-moving event.
    """
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    date: date
    event_type: EventType
    time_bucket: TimeBucket
    
    symbols: list[str] = Field(default_factory=list, description="Affected tickers")
    description: str
    expected_impact: str | None = None
    
    # Earnings-specific
    report_time: str | None = Field(None, description="pre-market/after-hours")
    consensus_eps: float | None = None
    
    # Fed speaker-specific
    speaker_name: str | None = None
```

### MacroIndicator

```python
class MacroIndicator(BaseModel):
    """
    A macro economic data point.
    """
    name: str = Field(..., description="Indicator name (DXY, CPI, etc.)")
    value: float
    previous_value: float | None = None
    trend: Trend
    
    updated_at: datetime
    source: str = Field(default="FRED", description="Data source")
    
    @property
    def change_pct(self) -> float | None:
        """Percentage change from previous value"""
        if self.previous_value and self.previous_value != 0:
            return ((self.value - self.previous_value) / self.previous_value) * 100
        return None
```

### MetalsAdvice

```python
class MetalsAdvice(BaseModel):
    """
    Gold/Silver timing recommendation.
    Constitution IV: Must account for DXY and Treasury correlation.
    """
    gld_action: MetalsAction
    slv_action: MetalsAction
    
    gld_price: float
    slv_price: float
    gld_rsi: float
    slv_rsi: float
    
    # Context (Constitution IV)
    dxy_value: float
    dxy_trend: Trend
    treasury_10y: float
    treasury_trend: Trend
    
    rationale: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
```

### IntelligenceReport

```python
class IntelligenceReport(BaseModel):
    """
    The daily consolidated report.
    """
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    status: ReportStatus = ReportStatus.COMPLETE
    
    # Agent outputs
    technical_scans: list[TradeRecommendation] = Field(
        default_factory=list,
        max_length=10,  # FR-009: Top 10 limit
        description="Top breakout candidates"
    )
    portfolio_alerts: list[PortfolioHolding] = Field(
        default_factory=list,
        description="Holdings with signals"
    )
    catalysts: list[CatalystEvent] = Field(
        default_factory=list,
        description="Upcoming market events"
    )
    macro_indicators: list[MacroIndicator] = Field(
        default_factory=list,
        description="Current macro readings"
    )
    metals_advice: MetalsAdvice | None = None
    
    # Data availability tracking
    unavailable_sections: list[str] = Field(
        default_factory=list,
        description="Sections that failed to load"
    )
    
    def mark_unavailable(self, section: str):
        """Mark a section as unavailable (FR-025)"""
        if section not in self.unavailable_sections:
            self.unavailable_sections.append(section)
        self.status = ReportStatus.PARTIAL
```

---

## Validation Rules Summary

| Entity | Field | Rule | Constitution |
|--------|-------|------|--------------|
| TradeRecommendation | entry, target, stop_loss | All required, non-null | I |
| TradeRecommendation | stop_loss | Must be entry * 0.975 | I |
| TradeRecommendation | market_cap (IBB) | Must be ≥ $500M | III |
| PortfolioHolding | signal | EXIT if pct_vs_sma ≤ -5% AND (position_pct > 10 OR pnl_pct < -10) | III |
| MetalsAdvice | dxy_value, dxy_trend | Required for recommendation | IV |
| MetalsAdvice | treasury_10y, treasury_trend | Required for recommendation | IV |
| IntelligenceReport | technical_scans | Max 10 items | FR-009 |

---

## State Transitions

### PortfolioHolding Signal Logic

```
                              ┌─────────────┐
                              │   ANALYZE   │
                              └──────┬──────┘
                                     │
                        ┌────────────┼────────────┐
                        ▼            ▼            ▼
              pct_vs_sma ≤ -5%   sentiment > 0.7   else
                        │        AND pct > 0      │
                        │            │            │
              ┌─────────┴─────────┐  │            │
              ▼                   ▼  ▼            ▼
    position > 10%          else    TOP_UP      HOLD
    OR loss > 10%             │
              │               │
              ▼               ▼
            EXIT            HEDGE
```

### IntelligenceReport Status

```
        ┌─────────────┐
        │   START     │
        └──────┬──────┘
               │
    All agents succeed?
        │           │
       YES          NO
        │           │
        ▼           ▼
    COMPLETE     PARTIAL
                    │
    Is market holiday?
        │
       YES
        │
        ▼
  MARKET_CLOSED
```
