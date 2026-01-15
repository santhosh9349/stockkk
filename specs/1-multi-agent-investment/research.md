# Research: Multi-Agent Investment Ecosystem

**Feature**: 1-multi-agent-investment  
**Date**: 2026-01-14  
**Purpose**: Resolve all NEEDS CLARIFICATION items and document technology decisions

---

## 1. Google ADK Agent Orchestration

### Decision: SequentialAgent as Root Controller

**Rationale**: The pipeline has strict ordering requirements (Technical Scanner must complete before Portfolio Analyst can access macro context for Metals Advisor). SequentialAgent guarantees deterministic execution order.

**Alternatives Considered**:
- `ParallelAgent`: Rejected - Agents have data dependencies (MetalsAdvisor needs macro context)
- `LoopAgent`: Rejected - No iterative refinement needed; single-pass pipeline
- Custom orchestration: Rejected - ADK provides battle-tested primitives

**Implementation Pattern**:
```python
from google.adk import SequentialAgent, Agent

orchestrator = SequentialAgent(
    name="AlphaAgentOrchestrator",
    agents=[
        technical_scanner,   # Gemini Flash
        portfolio_analyst,   # Gemini Pro
        catalyst_macro,      # Gemini Pro
        metals_advisor       # Gemini Pro (receives macro context)
    ]
)
```

---

## 2. Model Tiering Strategy

### Decision: Gemini 3 Flash for Scanner, Gemini 3 Pro for Analysis

**Rationale**:
- **TechnicalScannerAgent** processes ~600 tickers with simple numeric filters (RSI, Volume). Speed is critical; reasoning depth is not.
- **PortfolioAnalystAgent**, **CatalystMacroAgent**, **MetalsAdvisorAgent** require nuanced interpretation of sentiment, macro correlations, and position sizing. Higher reasoning capability justified.

**Cost/Performance Tradeoff**:
| Agent | Model | Est. Tokens/Run | Latency | Monthly Cost (30 runs) |
|-------|-------|-----------------|---------|------------------------|
| TechnicalScanner | Flash | ~50K | <30s | ~$1.50 |
| PortfolioAnalyst | Pro | ~10K | ~45s | ~$3.00 |
| CatalystMacro | Pro | ~15K | ~60s | ~$4.50 |
| MetalsAdvisor | Pro | ~5K | ~30s | ~$1.50 |
| **Total** | | ~80K | <3 min | ~$10.50/month |

---

## 3. MCP Tool Protocol Best Practices

### Decision: Read-Only Tool Definitions

**Rationale**: Constitution prohibits automated trade execution. All brokerage/data tools must be read-only to prevent accidental writes.

**Implementation Pattern**:
```python
from mcp import Tool, ToolResult

class AlphaVantageTool(Tool):
    """Read-only market data tool"""
    
    @tool_method(read_only=True)
    async def get_quote(self, symbol: str) -> ToolResult:
        ...
    
    @tool_method(read_only=True)
    async def get_rsi(self, symbol: str, period: int = 14) -> ToolResult:
        ...
    
    # NO write methods defined
```

**Verification**: CI pipeline includes static analysis to flag any tool method without `read_only=True`.

---

## 4. Alpha Vantage API Integration

### Decision: Free Tier with Aggressive Caching

**Rationale**: Free tier allows 5 calls/minute, 500 calls/day. Scanning 600 tickers requires batching and caching.

**Strategy**:
1. **Batch requests**: Use batch endpoints where available
2. **Cache RSI/SMA**: Technical indicators change slowly; cache for 5 minutes
3. **Prioritize**: Process high-liquidity ETF constituents first

**Rate Limit Handling**:
```python
from asyncio import Semaphore
from cachetools import TTLCache

class AlphaVantageClient:
    _semaphore = Semaphore(5)  # Max 5 concurrent
    _cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute cache
    
    async def get_with_rate_limit(self, endpoint: str):
        if endpoint in self._cache:
            return self._cache[endpoint]
        
        async with self._semaphore:
            await asyncio.sleep(12)  # Ensure 5 calls/min
            result = await self._fetch(endpoint)
            self._cache[endpoint] = result
            return result
```

---

## 5. FRED API Integration

### Decision: Direct API with Daily Caching

**Rationale**: Macro indicators (DXY, Treasury, CPI) update at most daily. Cache aggressively.

**Endpoints**:
| Indicator | FRED Series ID | Update Frequency |
|-----------|----------------|------------------|
| DXY (Dollar Index) | `DTWEXBGS` | Daily |
| 10Y Treasury | `DGS10` | Daily |
| CPI | `CPIAUCSL` | Monthly |
| PCE | `PCEPI` | Monthly |
| Fed Funds Rate | `FEDFUNDS` | Monthly |

---

## 6. News Sentiment Sources

### Decision: Verified Financial News APIs Only

**Rationale**: Constitution Principle II requires verified sources over web sentiment.

**Approved Sources** (priority order):
1. Bloomberg API (if available)
2. Finnhub News Sentiment
3. Alpha Vantage News Sentiment

**Rejected**: 
- Twitter/X sentiment (unverified, noisy)
- Reddit sentiment (Constitution II violation)
- General web search (Constitution II violation)

---

## 7. GitHub Actions Scheduling

### Decision: Cron at 13:00 UTC (08:00 EST) Weekdays Only

**Rationale**: Must complete by 08:30 AM EST for pre-market review.

**Timezone Handling**:
- GitHub Actions uses UTC
- EST = UTC-5 (standard time), EDT = UTC-4 (daylight time)
- Schedule for 13:00 UTC covers EST; manual adjustment needed for EDT transition

**Cron Expression**: `0 13 * * 1-5`
- `0` - Minute 0
- `13` - Hour 13 (UTC)
- `* *` - Any day, any month
- `1-5` - Monday through Friday

---

## 8. Telegram Bot Integration

### Decision: python-telegram-bot Library

**Rationale**: Official library, well-maintained, supports async, Markdown formatting.

**Setup Requirements**:
1. Create bot via @BotFather
2. Get chat ID via @userinfobot
3. Store in GitHub Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

**Message Format**:
```markdown
🚀 *Alpha-Agent Daily Report*
📅 2026-01-14 08:28 AM EST

*Top Picks*: AAPL, NVDA, MSFT
*Portfolio Alerts*: 2 EXIT, 1 HEDGE
*Metals*: GLD ACCUMULATE

[View Full Report](https://github.com/.../issues/123)
```

---

## 9. NYSE Holiday Calendar

### Decision: Static JSON + Runtime Validation

**Rationale**: NYSE publishes holidays annually. Static file is reliable; runtime check handles edge cases.

**2026 NYSE Holidays**:
```json
{
  "holidays": [
    "2026-01-01",  // New Year's Day
    "2026-01-19",  // MLK Day
    "2026-02-16",  // Presidents Day
    "2026-04-03",  // Good Friday
    "2026-05-25",  // Memorial Day
    "2026-07-03",  // Independence Day (observed)
    "2026-09-07",  // Labor Day
    "2026-11-26",  // Thanksgiving
    "2026-12-25"   // Christmas
  ]
}
```

---

## 10. Portfolio Storage Security

### Decision: Base64-Encoded GitHub Secret

**Rationale**: `portfolio.json` contains sensitive position data. Cannot commit to public repo.

**Workflow**:
1. User creates `portfolio.json` locally
2. Encodes: `base64 portfolio.json > portfolio.b64`
3. Stores content in GitHub Secret: `PORTFOLIO_JSON_BASE64`
4. Workflow decodes at runtime: `echo "$SECRET" | base64 -d > data/portfolio.json`

**Alternative Considered**: 
- Private repo for portfolio file: Rejected (adds complexity, splits codebase)
- Encrypted file in repo: Rejected (key management overhead)

---

## Summary

| Topic | Decision | Confidence |
|-------|----------|------------|
| Agent Orchestration | SequentialAgent | High |
| Model Tiering | Flash for scan, Pro for analysis | High |
| MCP Tools | Read-only enforcement | High |
| Alpha Vantage | Free tier + caching | Medium (may need upgrade) |
| FRED API | Direct with daily cache | High |
| News Sentiment | Bloomberg/Finnhub (verified only) | High |
| GitHub Actions | 13:00 UTC cron | High |
| Telegram | python-telegram-bot | High |
| Holiday Calendar | Static JSON | High |
| Portfolio Storage | Base64 GitHub Secret | High |

**All NEEDS CLARIFICATION items resolved.**
