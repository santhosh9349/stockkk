# Implementation Plan: Multi-Agent Investment Ecosystem (Alpha-Agent 2026)

**Branch**: `1-multi-agent-investment` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/1-multi-agent-investment/spec.md`

---

## Summary

Build a production-grade **Multi-Agent Investment Intelligence System** using Google ADK as the orchestration layer and MCP (Model Context Protocol) for financial data tool-calling. The system executes daily at 08:00 AM EST via GitHub Actions, running a deterministic pipeline of 4 specialized agents (Technical Scanner → Portfolio Analyst → Catalyst/Macro → Metals Advisor) that produces a consolidated Markdown report posted to a GitHub Issue with Telegram notification.

**Key Technical Decisions**:
- **SequentialAgent** root controller ensures deterministic, auditable execution order
- **Model tiering**: Gemini 3 Flash for high-volume scanning, Gemini 3 Pro for high-reasoning analysis
- **Read-only MCP tools**: No write operations to brokerage APIs (recommendation-only system)
- **Security-first**: All credentials via GitHub Secrets, portfolio data gitignored

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: google-adk (agent orchestration), mcp (tool protocol), httpx (async HTTP), pydantic (data models), python-telegram-bot (notifications)  
**Storage**: JSON file (portfolio.json - gitignored), GitHub Issues (reports)  
**Testing**: pytest + pytest-asyncio  
**Target Platform**: GitHub Actions runner (Ubuntu latest)  
**Project Type**: Single project (CLI-triggered agent pipeline)  
**Performance Goals**: Complete full pipeline in <25 minutes (5-minute buffer for 08:30 deadline)  
**Constraints**: <500MB memory, must handle API rate limits gracefully  
**Scale/Scope**: Single user, 4 ETF universes (~600 tickers), <50 portfolio holdings

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Implementation | Status |
|-----------|-------------|----------------|--------|
| **I. Financial Integrity** | Entry + Target + 2.5% Trailing Stop-Loss | `TradeRecommendation` model enforces all 3 fields as required; validation in `TechnicalScannerAgent` | ✅ PASS |
| **II. Data Governance** | Verified MCP servers over web sentiment | Tool priority: Alpha Vantage → FRED → Bloomberg; no general web search tools registered | ✅ PASS |
| **III. Risk Management (Biotech)** | Min $500M market cap for IBB | `biotech_filter()` in scanner excludes tickers below threshold | ✅ PASS |
| **III. Risk Management (Portfolio)** | -5% vs 20-day SMA → Exit/Hedge | `PortfolioAnalystAgent` implements Option B decision logic | ✅ PASS |
| **IV. Macro Correlation** | Metals weighted vs DXY + Treasury | `MetalsAdvisorAgent` receives macro context from upstream agent | ✅ PASS |
| **V. Operational Window** | Reports by 08:30 AM EST | Cron trigger at 08:00, 25-min pipeline budget, partial report fallback | ✅ PASS |

**Post-Design Re-Check**: All gates pass. No constitution violations.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GitHub Actions (08:00 AM EST)                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AlphaAgentOrchestrator (SequentialAgent)              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Technical  │  │  Portfolio  │  │  Catalyst   │  │   Metals    │     │
│  │   Scanner   │→ │   Analyst   │→ │   & Macro   │→ │   Advisor   │     │
│  │  (Flash)    │  │   (Pro)     │  │   (Pro)     │  │   (Pro)     │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │                │            │
│         ▼                ▼                ▼                ▼            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     MCP Tool Layer (Read-Only)                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │   │
│  │  │  Alpha   │  │   FRED   │  │ Bloomberg│  │  Market  │         │   │
│  │  │ Vantage  │  │   Data   │  │   News   │  │ Calendar │         │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Report Generator                                 │
│  ┌──────────────────┐                    ┌──────────────────┐           │
│  │   GitHub Issue   │                    │  Telegram Bot    │           │
│  │  (Full Report)   │                    │  (Summary + Link)│           │
│  └──────────────────┘                    └──────────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

### Documentation (this feature)

```
specs/1-multi-agent-investment/
├── plan.md              # This file
├── research.md          # Phase 0: Technology research
├── data-model.md        # Phase 1: Entity schemas
├── quickstart.md        # Phase 1: Local dev setup
├── contracts/           # Phase 1: API contracts
│   ├── trade_recommendation.schema.json
│   ├── portfolio_holding.schema.json
│   ├── intelligence_report.schema.json
│   └── mcp_tools.yaml
└── tasks.md             # Phase 2: Atomic implementation tasks
```

### Source Code (repository root)

```
alpha-agent-2026/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point: CLI + orchestrator init
│   │
│   ├── agents/                    # Google ADK Agent definitions
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # SequentialAgent root controller
│   │   ├── technical_scanner.py   # Gemini Flash - breakout detection
│   │   ├── portfolio_analyst.py   # Gemini Pro - holdings analysis
│   │   ├── catalyst_macro.py      # Gemini Pro - event/macro tracking
│   │   └── metals_advisor.py      # Gemini Pro - Gold/Silver timing
│   │
│   ├── tools/                     # MCP Tool definitions (READ-ONLY)
│   │   ├── __init__.py
│   │   ├── alpha_vantage.py       # Stock quotes, technicals, fundamentals
│   │   ├── fred_data.py           # Macro indicators (DXY, Treasury, CPI)
│   │   ├── news_sentiment.py      # Bloomberg/verified news sentiment
│   │   ├── market_calendar.py     # NYSE holidays, earnings calendar
│   │   └── portfolio_reader.py    # Read portfolio.json (no writes)
│   │
│   ├── models/                    # Pydantic data models
│   │   ├── __init__.py
│   │   ├── trade_recommendation.py
│   │   ├── portfolio_holding.py
│   │   ├── catalyst_event.py
│   │   ├── macro_indicator.py
│   │   └── intelligence_report.py
│   │
│   ├── utils/                     # Shared utilities
│   │   ├── __init__.py
│   │   ├── config.py              # Environment variable loading
│   │   ├── logging.py             # Structured logging setup
│   │   ├── retry.py               # Exponential backoff decorator
│   │   └── formatters.py          # Markdown report formatting
│   │
│   └── delivery/                  # Report delivery mechanisms
│       ├── __init__.py
│       ├── github_issue.py        # Create/update GitHub Issues
│       └── telegram_bot.py        # Send Telegram notifications
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_technical_scanner.py
│   │   ├── test_portfolio_analyst.py
│   │   └── test_biotech_filter.py
│   ├── integration/
│   │   ├── test_alpha_vantage_tool.py
│   │   ├── test_fred_tool.py
│   │   └── test_full_pipeline.py
│   └── contract/
│       └── test_report_schema.py
│
├── .github/
│   └── workflows/
│       └── daily_scan.yml         # Cron: 08:00 AM EST
│
├── data/
│   ├── portfolio.example.json     # Mock data for CI/testing
│   └── nyse_holidays_2026.json    # Holiday calendar
│
├── .env.example                   # Template for local development
├── .gitignore                     # Includes portfolio.json, .env
├── pyproject.toml                 # Project config + dependencies
├── requirements.txt               # Pinned dependencies
└── README.md                      # Project documentation
```

**Structure Decision**: Single project with clear separation of concerns. Agents, tools, models, and delivery are isolated modules. No frontend/backend split needed (headless pipeline).

---

## Agent Specifications

### 1. TechnicalScannerAgent (Gemini 3 Flash)

**Purpose**: High-volume stock screening across 4 ETF universes  
**Model**: `gemini-3-flash` (optimized for speed with large datasets)  
**Tools**: `alpha_vantage.get_rsi()`, `alpha_vantage.get_volume()`, `alpha_vantage.get_market_cap()`

**Logic**:
```python
# Pseudo-code for core filtering logic
for ticker in QQQ + IBB + ITA + SPY:
    rsi = get_rsi(ticker, period=14)
    volume = get_volume(ticker)
    avg_volume = get_avg_volume(ticker, period=20)
    
    # RSI crossover filter
    rsi_signal = rsi < 30 or (rsi > 50 and prev_rsi < 50)
    
    # Volume spike filter  
    volume_signal = volume > (avg_volume * 1.5)
    
    # Biotech floor (Constitution III)
    if ticker in IBB_UNIVERSE:
        market_cap = get_market_cap(ticker)
        if market_cap < 500_000_000:
            continue  # Skip micro-caps
    
    if rsi_signal and volume_signal:
        # Calculate trade parameters (Constitution I)
        entry = current_price
        target = calculate_target(ticker)  # Based on resistance levels
        stop_loss = entry * 0.975  # 2.5% trailing stop
        
        recommendations.append(TradeRecommendation(...))

# Rank by confidence, return top 10
return sorted(recommendations, key=lambda x: x.confidence)[:10]
```

### 2. PortfolioAnalystAgent (Gemini 3 Pro)

**Purpose**: Analyze existing holdings for health signals  
**Model**: `gemini-3-pro` (high-reasoning for nuanced decisions)  
**Tools**: `portfolio_reader.get_holdings()`, `alpha_vantage.get_sma()`, `news_sentiment.get_sentiment()`

**Logic (Option B - Constitution III)**:
```python
for holding in portfolio:
    sma_20 = get_sma(holding.symbol, period=20)
    current_price = get_price(holding.symbol)
    pct_vs_sma = (current_price - sma_20) / sma_20 * 100
    
    position_pct = holding.value / total_portfolio_value * 100
    loss_pct = (current_price - holding.cost_basis) / holding.cost_basis * 100
    
    sentiment = get_sentiment(holding.symbol)
    
    if pct_vs_sma <= -5:
        # Constitution III trigger
        if position_pct > 10 or loss_pct < -10:
            signal = "EXIT"
        else:
            signal = "HEDGE"
    elif sentiment > 0.7 and pct_vs_sma > 0:
        signal = "TOP-UP"
    else:
        signal = "HOLD"
    
    alerts.append(PortfolioAlert(holding, signal, rationale))
```

### 3. CatalystMacroAgent (Gemini 3 Pro)

**Purpose**: Track market-moving events and macro indicators  
**Model**: `gemini-3-pro`  
**Tools**: `market_calendar.get_earnings()`, `fred_data.get_fed_rate()`, `fred_data.get_dxy()`, `fred_data.get_treasury_10y()`, `fred_data.get_cpi()`

**Output Structure**:
```
Catalysts:
├── Today: [Earnings: AAPL pre-market, MSFT after-hours]
├── This Week: [Jobs Report Fri, Fed Speaker Wed]
└── 3-Month Horizon: [Q1 GDP, Fed Meeting Mar 18]

Macro Dashboard:
├── Fed Rate Probability: 78% hold (CME FedWatch equivalent)
├── DXY: 104.2 (↑ strengthening)
├── 10Y Treasury: 4.35% (↑ rising)
├── CPI: 3.1% YoY (latest release)
└── PCE: 2.8% YoY (latest release)
```

### 4. MetalsAdvisorAgent (Gemini 3 Pro)

**Purpose**: Gold/Silver timing advice weighted against macro context  
**Model**: `gemini-3-pro`  
**Tools**: `alpha_vantage.get_price(GLD, SLV)`, receives macro context from CatalystMacroAgent

**Logic (Constitution IV)**:
```python
dxy_trend = macro_context.dxy.trend  # "strengthening" | "weakening"
treasury_trend = macro_context.treasury_10y.trend
geopolitical_tension = get_geopolitical_index()  # From news sentiment

gld_rsi = get_rsi("GLD")
slv_rsi = get_rsi("SLV")

if dxy_trend == "strengthening":
    # Inverse correlation opportunity
    recommendation = "ACCUMULATE"
    rationale = "DXY strength typically precedes metals recovery"
elif geopolitical_tension > 0.8 and (gld_rsi > 70 or slv_rsi > 70):
    recommendation = "PROFIT-TAKE"
    rationale = "Overbought conditions during peak tension"
else:
    recommendation = "HOLD"
```

---

## MCP Tool Definitions (Read-Only)

All tools are **read-only** per security requirements. No write operations to any brokerage or trading API.

| Tool | Source | Operations | Rate Limit |
|------|--------|------------|------------|
| `alpha_vantage` | Alpha Vantage API | `get_quote`, `get_rsi`, `get_sma`, `get_volume`, `get_market_cap` | 5 calls/min (free tier) |
| `fred_data` | FRED API | `get_dxy`, `get_treasury_10y`, `get_cpi`, `get_pce`, `get_fed_funds` | 120 calls/min |
| `news_sentiment` | Bloomberg/Verified | `get_sentiment(ticker)` | Per provider limits |
| `market_calendar` | NYSE/Earnings APIs | `is_market_holiday`, `get_earnings_today`, `get_fed_speakers` | N/A (cached daily) |
| `portfolio_reader` | Local JSON | `get_holdings()` | N/A (local file) |

---

## Security & Data Protection

### Credentials Management

```python
# src/utils/config.py
import os

class Config:
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    FRED_API_KEY = os.getenv("FRED_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Provided by Actions
    
    @classmethod
    def validate(cls):
        required = ["ALPHA_VANTAGE_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise EnvironmentError(f"Missing required env vars: {missing}")
```

### .gitignore Entries

```gitignore
# Sensitive data
.env
portfolio.json

# Keep example files
!portfolio.example.json
!.env.example
```

### Portfolio Data

```json
// data/portfolio.example.json (committed - mock data)
{
  "holdings": [
    {"symbol": "AAPL", "shares": 100, "cost_basis": 150.00, "entry_date": "2025-06-15"},
    {"symbol": "NVDA", "shares": 50, "cost_basis": 450.00, "entry_date": "2025-08-01"}
  ],
  "last_updated": "2026-01-14T08:00:00Z"
}
```

---

## CI/CD Pipeline

### .github/workflows/daily_scan.yml

```yaml
name: Alpha-Agent Daily Scan

on:
  schedule:
    # 08:00 AM EST = 13:00 UTC (during EST, 12:00 UTC during EDT)
    - cron: '0 13 * * 1-5'  # Weekdays only
  workflow_dispatch:  # Manual trigger for testing

env:
  PYTHON_VERSION: '3.11'

jobs:
  daily-intelligence:
    runs-on: ubuntu-latest
    timeout-minutes: 30  # Hard cutoff before 08:30 deadline
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Check market holiday
        id: holiday-check
        env:
          ALPHA_VANTAGE_API_KEY: ${{ secrets.ALPHA_VANTAGE_API_KEY }}
        run: |
          python -c "from src.tools.market_calendar import is_market_holiday; print(f'holiday={is_market_holiday()}')" >> $GITHUB_OUTPUT
      
      - name: Run Alpha-Agent Pipeline
        if: steps.holiday-check.outputs.holiday != 'True'
        env:
          ALPHA_VANTAGE_API_KEY: ${{ secrets.ALPHA_VANTAGE_API_KEY }}
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PORTFOLIO_PATH: ${{ secrets.PORTFOLIO_JSON_BASE64 }}
        run: |
          # Decode portfolio from secret (base64 encoded)
          echo "$PORTFOLIO_PATH" | base64 -d > data/portfolio.json
          python -m src.main --output github-issue --notify telegram
      
      - name: Post Market Closed Notice
        if: steps.holiday-check.outputs.holiday == 'True'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m src.main --market-closed
```

---

## Error Handling & Fallback

### Retry Strategy (FR-025)

```python
# src/utils/retry.py
import asyncio
from functools import wraps

def with_retry(max_attempts=3, base_delay=1.0, max_delay=30.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    await asyncio.sleep(delay)
            
            # Return sentinel indicating failure
            return DataUnavailable(source=func.__name__, error=str(last_exception))
        return wrapper
    return decorator
```

### Partial Report Generation

```python
# src/agents/orchestrator.py
class AlphaAgentOrchestrator:
    async def run(self) -> IntelligenceReport:
        report = IntelligenceReport(timestamp=datetime.now())
        
        # Each agent returns result or DataUnavailable
        report.technical_scans = await self.technical_scanner.run()
        report.portfolio_health = await self.portfolio_analyst.run()
        report.catalysts = await self.catalyst_macro.run()
        report.metals_advice = await self.metals_advisor.run(
            macro_context=report.catalysts.macro_indicators
        )
        
        # Mark unavailable sections in report
        report.mark_unavailable_sections()
        
        return report
```

---

<!-- 
## Atomic Tasks (Superseded)

This preliminary task outline has been superseded by the comprehensive 
tasks.md file (79 tasks across 8 phases). See: specs/1-multi-agent-investment/tasks.md
-->

---

## Complexity Tracking

No constitution violations requiring justification. Design adheres to all 5 principles.

---

**Plan Status**: ✅ Complete  
**Next Step**: `/speckit.tasks` to generate atomic task list
