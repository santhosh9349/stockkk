# Feature Specification: Multi-Agent Investment Ecosystem

**Feature Branch**: `1-multi-agent-investment`  
**Created**: 2026-01-14  
**Status**: Planned  
**Input**: User description: "Multi-Agent Investment Ecosystem built with Google ADK and GitHub Actions - a daily automated intelligence suite triggered at 8 AM via GitHub Actions with Technical Scanner, Portfolio Health, Catalyst & Macro, and Metals Advisor agents."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Morning Intelligence Report (Priority: P1)

As an investor, I want to receive a comprehensive daily intelligence report by 8:30 AM EST so that I can make informed pre-market decisions before the market opens at 9:30 AM EST.

**Why this priority**: This is the core value proposition - delivering timely, actionable intelligence before trading begins. Without this, no other agent functionality matters.

**Independent Test**: Can be fully tested by triggering the GitHub Action at 8 AM EST and verifying a complete Markdown report is posted to a GitHub Issue with all agent sections populated and a mobile notification is received.

**Acceptance Scenarios**:

1. **Given** the system is configured with valid API credentials and holdings data, **When** the GitHub Action triggers at 8:00 AM EST, **Then** a complete intelligence report is posted to a GitHub Issue by 8:30 AM EST.
2. **Given** the report is generated successfully, **When** the report is posted, **Then** a mobile-friendly notification is sent with a summary and link to the full report.
3. **Given** any agent fails to complete within the time window, **When** the 8:30 AM deadline approaches, **Then** partial results are posted with clear indication of which agents timed out.

---

### User Story 2 - Technical Breakout Detection (Priority: P1)

As an investor, I want to receive a filtered list of high-probability breakout candidates from major indices so that I can identify new entry opportunities with defined risk parameters.

**Why this priority**: Trade discovery is fundamental to portfolio growth. This directly implements Constitution Principle I (Financial Integrity) requiring Entry, Target, and 2.5% Trailing Stop-Loss.

**Independent Test**: Can be fully tested by running the Technical Scanner Agent independently and verifying it returns stocks with complete trade parameters (Entry, Target, Stop-Loss) from QQQ, IBB, ITA, and SPY universes.

**Acceptance Scenarios**:

1. **Given** market data is available from verified MCP servers, **When** the Technical Scanner runs, **Then** it returns only stocks with RSI crossing below 30 OR crossing above 50, AND volume > 1.5x 20-day average.
2. **Given** a stock meets technical criteria, **When** it is included in the report, **Then** it includes calculated Entry price, Target price, and 2.5% Trailing Stop-Loss level.
3. **Given** a Biotech stock (IBB universe) is detected, **When** evaluating for inclusion, **Then** it is excluded if market cap is below $500M per Constitution Principle III.

---

### User Story 3 - Portfolio Health Monitoring (Priority: P1)

As an investor with existing holdings, I want to receive proactive alerts about my portfolio's health so that I can protect capital and optimize positions.

**Why this priority**: Capital preservation is non-negotiable. This implements Constitution Principle III requiring immediate 'Exit' or 'Hedge' alerts when holdings show -5% trend against 20-day SMA.

**Independent Test**: Can be fully tested by providing a test portfolio JSON with holdings at various performance levels and verifying correct 'Top-up', 'Hold', 'Exit', and 'Hedge' classifications.

**Acceptance Scenarios**:

1. **Given** a holding is trending -5% or worse against its 20-day SMA, **When** the Portfolio Health Agent analyzes it, **Then** an immediate 'Exit' or 'Hedge' alert is generated with specific action recommendation.
2. **Given** a holding has positive momentum and favorable news sentiment, **When** analyzed, **Then** a 'Top-up' signal is generated with rationale.
3. **Given** a holding has negative news sentiment from verified sources, **When** analyzed, **Then** a warning is included even if technical indicators are neutral.

---

### User Story 4 - Catalyst Calendar Intelligence (Priority: P2)

As an investor, I want to see upcoming market-moving events organized by time horizon so that I can position ahead of catalysts and avoid surprises.

**Why this priority**: Event-driven positioning improves returns but is secondary to core scanning and portfolio protection.

**Independent Test**: Can be fully tested by running the Catalyst Agent and verifying it returns events categorized into 'Today', 'This Week', and '3-Month Horizon' buckets with specific dates and expected impact.

**Acceptance Scenarios**:

1. **Given** the current date, **When** the Catalyst Agent runs, **Then** it returns events grouped into 'Today' (Earnings, PDUFA dates), 'This Week' (Jobs data, Fed speakers), and '3-Month Horizon' (cyclical trends, major economic releases).
2. **Given** macro data sources are available, **When** analyzing the macro environment, **Then** Fed Rate probability, DXY trend, and latest CPI/PCE readings are included.
3. **Given** an earnings event is 'Today', **When** included in the report, **Then** expected report time (pre-market/after-hours) and consensus estimates are provided.

---

### User Story 5 - Metals Timing Advisor (Priority: P2)

As an investor interested in precious metals, I want advice on Gold and Silver timing that accounts for macro correlations so that I can optimize entry and exit points.

**Why this priority**: Metals are a portfolio diversifier. This directly implements Constitution Principle IV requiring DXY and Treasury yield correlation.

**Independent Test**: Can be fully tested by running the Metals Advisor with various DXY and Treasury yield scenarios and verifying recommendations align with the correlation logic.

**Acceptance Scenarios**:

1. **Given** DXY is strengthening (uptrend), **When** the Metals Advisor runs, **Then** it recommends accumulation phases for Gold/Silver (inverse correlation opportunity).
2. **Given** geopolitical tension indicators are elevated, **When** combined with technical overbought conditions, **Then** it recommends profit-taking or position reduction.
3. **Given** 10-year Treasury yields are rising, **When** analyzing metals, **Then** the yield context is factored into the accumulation/distribution recommendation.

---

### Edge Cases

- What happens when MCP data servers (Alpha Vantage, FRED, Bloomberg) are unavailable or return errors?
- How does the system handle when the GitHub Action fails to trigger at the scheduled time?
- What happens when the portfolio JSON/database contains invalid or stale data?
- How does the system handle market holidays when exchanges are closed?
- What happens when a stock in the scan universe is halted or delisted?
- How does the system handle when mobile notification service is unavailable?

## Requirements *(mandatory)*

### Functional Requirements

**Agent Orchestration**
- **FR-001**: System MUST use Google ADK for agent orchestration and coordination.
- **FR-002**: System MUST use MCP (Model Context Protocol) for all financial data tool-calling.
- **FR-003**: System MUST prioritize data from verified MCP servers (Alpha Vantage, FRED, Bloomberg) over general web-search sentiment per Constitution Principle II.

**Technical Scanner Agent**
- **FR-004**: System MUST scan stocks from QQQ (NASDAQ 100), IBB (Biotech), ITA (Aerospace/Defense), and SPY (S&P 500) universes.
- **FR-005**: System MUST filter for stocks with RSI crossing below 30 OR RSI crossing above 50 from below (crossover detected within previous 2 trading sessions).
- **FR-006**: System MUST filter for stocks with volume exceeding 1.5x the 20-day average volume.
- **FR-007**: System MUST exclude Biotech stocks (IBB universe) with market capitalization below $500M per Constitution Principle III.
- **FR-008**: System MUST calculate and include Entry price, Target price, and 2.5% Trailing Stop-Loss for every trade recommendation per Constitution Principle I. Trailing stop adjusts upward as price increases, maintaining 2.5% below the highest price since entry.
- **FR-009**: System MUST limit Technical Scanner output to top 10 recommendations, ranked by confidence/signal strength (strongest signals first).

**Portfolio Health Agent**
- **FR-010**: System MUST accept portfolio holdings from a secure JSON file or database.
- **FR-011**: System MUST cross-reference holdings with real-time news sentiment from verified sources.
- **FR-012**: System MUST generate 'Exit' or 'Hedge' alerts for any holding showing -5% or worse trend against its 20-day SMA per Constitution Principle III. Decision logic: 'Exit' for positions >10% of portfolio OR losses >-10%; 'Hedge' for smaller positions with moderate losses.
- **FR-013**: System MUST generate 'Top-up' signals for holdings with positive momentum and favorable sentiment.

**Catalyst & Macro Agent**
- **FR-014**: System MUST categorize events into 'Today', 'This Week', and '3-Month Horizon' time buckets.
- **FR-015**: System MUST track and report Fed Rate probability (CME FedWatch equivalent data).
- **FR-016**: System MUST track and report DXY (Dollar Index) trend.
- **FR-017**: System MUST track and report latest CPI and PCE inflation data.

**Metals Advisor Agent**
- **FR-018**: System MUST provide Gold (GLD) and Silver (SLV) timing advice.
- **FR-019**: System MUST weight metals advice against current DXY trend and 10-year Treasury yields per Constitution Principle IV.
- **FR-020**: System MUST recommend accumulation during DXY strength periods.
- **FR-021**: System MUST recommend profit-taking during peak geopolitical tension (geopolitical_index > 0.8) combined with overbought conditions (RSI > 70).

**Report Delivery & Operations**
- **FR-022**: System MUST trigger daily at 8:00 AM EST via GitHub Actions.
- **FR-023**: System MUST complete all scans and deliver reports by 8:30 AM EST per Constitution Principle V.
- **FR-024**: System MUST post a comprehensive Markdown summary to a GitHub Issue.
- **FR-025**: System MUST send a mobile-friendly notification via Telegram Bot API with report summary (≤280 chars) and link to full GitHub Issue.
- **FR-026**: System MUST retry failed data source requests with exponential backoff (up to 3 attempts), then proceed with available data and clearly mark affected sections as 'Data Unavailable' in the report.
- **FR-027**: System MUST detect NYSE market holidays before execution; on holidays, skip all agents and post a 'Market Closed' notice to GitHub Issue instead of a full report.

**Edge Case Handling**
- **FR-028**: System MUST skip halted or delisted stocks during scanning and log a warning without failing the pipeline.
- **FR-029**: System MUST validate portfolio JSON schema on load; invalid entries are skipped with warning, stale data (>24h) triggers a notice in the report header.
- **FR-030**: System MUST queue Telegram notification for retry (up to 3 attempts) if delivery fails; if all retries fail, log error but do not fail the pipeline.

### Key Entities

- **Trade Recommendation**: A potential trade opportunity with symbol, Entry price, Target price, 2.5% Trailing Stop-Loss, technical indicators (RSI, Volume), and confidence level.
- **Portfolio Holding**: A current position with symbol, entry date, cost basis, current price, P&L, 20-day SMA relationship, and sentiment score.
- **Catalyst Event**: A market-moving event with date, type (Earnings/PDUFA/Economic), affected symbols, expected impact, and time bucket classification.
- **Macro Indicator**: A macro data point with indicator name (DXY, Fed Rate, CPI, PCE, Treasury Yield), current value, trend direction, and last updated timestamp.
- **Metals Advice**: Gold/Silver timing recommendation with action (Accumulate/Hold/Profit-Take), DXY value and trend, 10Y Treasury yield and trend, RSI levels, and rationale.
- **Intelligence Report**: The daily output containing sections for Technical Scans, Portfolio Health, Catalysts, Macro Overview, and Metals Advice with generation timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Daily intelligence report is delivered to GitHub Issue by 8:30 AM EST on 95% of trading days.
- **SC-002**: 100% of trade recommendations include Entry, Target, and 2.5% Trailing Stop-Loss (zero exceptions).
- **SC-003**: Mobile notification is received within 5 minutes of report posting on 95% of trading days.
- **SC-004**: Technical Scanner identifies breakout candidates with >60% historical accuracy over 30-day rolling window.
- **SC-005**: Portfolio Health Agent correctly flags 100% of holdings breaching -5% vs 20-day SMA threshold.
- **SC-006**: Zero Biotech recommendations with market cap below $500M threshold.
- **SC-007**: Metals advice correctly correlates with DXY direction 80% of the time (accumulate on DXY strength, caution on DXY weakness).
- **SC-008**: System gracefully handles data source failures, delivering partial reports rather than complete failures.

## Clarifications

### Session 2026-01-14

- Q: What criteria should determine 'Exit' vs 'Hedge' recommendation when holding breaches -5% SMA threshold? → A: System decides based on position size and loss magnitude (automated risk-based logic).
- Q: What is the fallback behavior when data sources are unavailable? → A: Retry with exponential backoff (up to 3 attempts), then deliver partial report with unavailable sections marked.
- Q: How should the system handle market holidays? → A: Skip execution entirely, post 'Market Closed' notice to GitHub Issue.
- Q: What is the maximum number of trade recommendations per report? → A: Top 10 recommendations, ranked by confidence/signal strength.
- Q: What mobile notification channel should be used? → A: Telegram Bot API (free, Markdown support, no app development needed).

## Assumptions

- User has valid API credentials for Alpha Vantage, FRED, and/or Bloomberg MCP servers.
- User has a GitHub repository configured with Actions enabled and appropriate secrets.
- User has a mobile notification service configured (assumed: standard push notification or SMS gateway).
- Portfolio holdings data is maintained in a JSON file or accessible database with standard schema.
- Market data is available during pre-market hours (4:00 AM - 9:30 AM EST) for analysis.
- GitHub Actions runners are available and can complete within the 30-minute operational window.

## Out of Scope

- Real-time intraday alerts (system runs once daily at 8 AM EST).
- Automated trade execution (system provides recommendations only).
- Backtesting infrastructure for strategy validation.
- Historical performance tracking and reporting.
- Multi-user support or authentication (single-user system).
- Options or derivatives analysis.
- Cryptocurrency markets.
