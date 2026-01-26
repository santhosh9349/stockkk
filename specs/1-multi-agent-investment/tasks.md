# Tasks: Multi-Agent Investment Ecosystem (Alpha-Agent 2026)

**Input**: Design documents from `/specs/1-multi-agent-investment/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included per plan.md requirements (unit, integration, contract tests)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1-US5) this task belongs to
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure per plan.md in alpha-agent-2026/
- [X] T002 Initialize Python project with pyproject.toml (Python 3.11+, dependencies: google-adk, mcp, httpx, pydantic, python-telegram-bot, pytest, pytest-asyncio)
- [X] T003 [P] Create requirements.txt with pinned dependency versions
- [X] T004 [P] Create .gitignore (include portfolio.json, .env, __pycache__, .pytest_cache)
- [X] T005 [P] Create .env.example template with all required environment variables
- [X] T006 [P] Configure pytest in pyproject.toml and create tests/conftest.py with shared fixtures

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement Config class with env var loading and validation in src/utils/config.py
- [X] T008 [P] Implement retry decorator with exponential backoff (3 attempts, base 1s) in src/utils/retry.py
- [X] T009 [P] Implement structured logging utility in src/utils/logging.py
- [X] T010 [P] Create enumerations (Universe, Signal, EventType, TimeBucket, Trend, ReportStatus, MetalsAction) in src/models/__init__.py
- [X] T011 Create data/ directory with nyse_holidays_2026.json (NYSE holiday calendar)
- [X] T012 Create data/portfolio.example.json with mock holdings data for testing

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Morning Intelligence Report (Priority: P1) 🎯 MVP

**Goal**: Deliver comprehensive daily intelligence report by 8:30 AM EST via GitHub Issue + Telegram notification

**Independent Test**: Trigger pipeline manually, verify GitHub Issue created with all sections, Telegram notification received

### Data Models for US1

- [X] T013 [P] [US1] Create IntelligenceReport Pydantic model with status, unavailable_sections tracking in src/models/intelligence_report.py
- [X] T014 [P] [US1] Create DataUnavailable sentinel class for partial report handling in src/models/intelligence_report.py

### Delivery Infrastructure for US1

- [X] T015 [US1] Implement Markdown report formatter with section templates in src/utils/formatters.py
- [X] T016 [US1] Implement GitHub Issue reporter (create/update issues via API) in src/delivery/github_issue.py (depends on T015)
- [X] T017 [US1] Implement Telegram bot notifier (summary + link to issue) in src/delivery/telegram_bot.py (depends on T015)

### Orchestration for US1

- [X] T018 [US1] Implement AlphaAgentOrchestrator (Google ADK SequentialAgent) in src/agents/orchestrator.py
- [X] T019 [US1] Implement partial report fallback logic (mark unavailable sections) in src/agents/orchestrator.py
- [X] T020 [US1] Create CLI entry point with --output and --notify flags in src/main.py

### CI/CD for US1

- [X] T021 [US1] Create .github/workflows/daily_scan.yml with cron trigger (08:00 AM EST = 13:00 UTC, weekdays)
- [X] T022 [US1] Add market-closed mode (--market-closed flag) posting holiday notice in src/main.py

### Edge Case Handling for US1

- [X] T022a [US1] Implement halted/delisted stock detection and skip logic in src/tools/alpha_vantage.py (FR-028)
- [X] T022b [US1] Implement portfolio JSON schema validation with stale data detection in src/tools/portfolio_reader.py (FR-029)
- [X] T022c [US1] Implement Telegram notification retry queue (3 attempts) in src/delivery/telegram_bot.py (FR-030)

### Tests for US1

- [X] T023 [P] [US1] Unit test for IntelligenceReport model and partial report marking in tests/unit/test_models.py
- [X] T024 [P] [US1] Unit test for Markdown formatter output structure in tests/unit/test_formatters.py
- [X] T025 [US1] Integration test for full pipeline with mocked agents in tests/integration/test_full_pipeline.py

**Checkpoint**: US1 complete - can trigger daily workflow, receive GitHub Issue + Telegram notification (with placeholder agent data)

---

## Phase 4: User Story 2 - Technical Breakout Detection (Priority: P1)

**Goal**: Scan QQQ/IBB/ITA/SPY for breakout candidates with Entry/Target/2.5% Stop-Loss

**Independent Test**: Run TechnicalScannerAgent, verify top 10 recommendations with complete trade parameters, biotech filter applied

### Data Models for US2

- [X] T026 [P] [US2] Create TradeRecommendation Pydantic model with Constitution I validation (entry, target, stop_loss required, 2.5% validation) in src/models/trade_recommendation.py

### MCP Tools for US2

- [X] T027 [P] [US2] Implement alpha_vantage tool base class with rate limiting and caching in src/tools/alpha_vantage.py
- [X] T028 [US2] Implement get_quote, get_rsi, get_sma, get_volume methods in src/tools/alpha_vantage.py
- [X] T029 [US2] Implement get_market_cap method for biotech filter in src/tools/alpha_vantage.py

### Agent Implementation for US2

- [X] T030 [US2] Implement TechnicalScannerAgent with Gemini 3 Flash model in src/agents/technical_scanner.py
- [X] T031 [US2] Implement RSI crossover filter (RSI < 30 OR RSI crossing 50 from below) in src/agents/technical_scanner.py
- [X] T032 [US2] Implement volume spike filter (> 1.5x 20-day average) in src/agents/technical_scanner.py
- [X] T033 [US2] Implement biotech_filter excluding IBB tickers with market cap < $500M in src/agents/technical_scanner.py
- [X] T034 [US2] Implement trade parameter calculation (entry, target, 2.5% trailing stop with `high_water_mark` state variable tracking max price since entry) in src/agents/technical_scanner.py
- [X] T035 [US2] Implement confidence ranking and top 10 limit (FR-009) in src/agents/technical_scanner.py

### Tests for US2

- [X] T036 [P] [US2] Unit test for TradeRecommendation validation (stop_loss must be entry * 0.975) in tests/unit/test_models.py
- [X] T037 [P] [US2] Unit test for biotech_filter ($500M threshold) in tests/unit/test_biotech_filter.py
- [X] T038 [US2] Contract test for TradeRecommendation against JSON schema in tests/contract/test_report_schema.py

**Checkpoint**: US2 complete - Technical Scanner produces valid trade recommendations with all Constitution I fields

---

## Phase 5: User Story 3 - Portfolio Health Monitoring (Priority: P1)

**Goal**: Analyze existing holdings, generate Exit/Hedge/Top-up signals based on SMA and sentiment

**Independent Test**: Provide test portfolio JSON, verify correct signal classification per Option B logic

### Data Models for US3

- [X] T039 [P] [US3] Create PortfolioHolding Pydantic model with computed fields (pct_vs_sma, position_pct, pnl_pct, signal) in src/models/portfolio_holding.py

### MCP Tools for US3

- [X] T040 [P] [US3] Implement portfolio_reader tool (read portfolio.json, no writes) in src/tools/portfolio_reader.py
- [X] T041 [P] [US3] Implement news_sentiment tool (Bloomberg/Finnhub verified sources only) in src/tools/news_sentiment.py

### Agent Implementation for US3

- [X] T042 [US3] Implement PortfolioAnalystAgent with Gemini 3 Pro model in src/agents/portfolio_analyst.py
- [X] T043 [US3] Implement 20-day SMA comparison logic in src/agents/portfolio_analyst.py
- [X] T044 [US3] Implement Option B Exit/Hedge decision logic (EXIT if position > 10% OR loss > 10%, else HEDGE) in src/agents/portfolio_analyst.py
- [X] T045 [US3] Implement Top-up signal logic (positive momentum + favorable sentiment) in src/agents/portfolio_analyst.py
- [X] T046 [US3] Implement sentiment cross-reference with news sources in src/agents/portfolio_analyst.py

### Tests for US3

- [X] T047 [P] [US3] Unit test for PortfolioHolding model computed properties in tests/unit/test_models.py
- [X] T048 [US3] Unit test for Option B logic (EXIT vs HEDGE conditions) in tests/unit/test_portfolio_analyst.py
- [X] T049 [US3] Contract test for PortfolioHolding against JSON schema in tests/contract/test_report_schema.py

**Checkpoint**: US3 complete - Portfolio Health correctly flags holdings with Exit/Hedge/Top-up signals per Constitution III

---

## Phase 6: User Story 4 - Catalyst Calendar Intelligence (Priority: P2)

**Goal**: Track market-moving events organized by Today/This Week/3-Month Horizon with macro indicators

**Independent Test**: Run CatalystMacroAgent, verify events categorized by time bucket, macro indicators populated

### Data Models for US4

- [X] T050 [P] [US4] Create CatalystEvent Pydantic model with time_bucket classification in src/models/catalyst_event.py
- [X] T051 [P] [US4] Create MacroIndicator Pydantic model with trend calculation in src/models/macro_indicator.py

### MCP Tools for US4

- [X] T052 [P] [US4] Implement market_calendar tool (is_market_holiday, get_earnings_today, get_fed_speakers) in src/tools/market_calendar.py
- [X] T053 [P] [US4] Implement fred_data tool base with daily caching in src/tools/fred_data.py
- [X] T054 [US4] Implement get_dxy, get_treasury_10y, get_cpi, get_pce, get_fed_funds methods in src/tools/fred_data.py

### Agent Implementation for US4

- [X] T055 [US4] Implement CatalystMacroAgent with Gemini 3 Pro model in src/agents/catalyst_macro.py
- [X] T056 [US4] Implement event categorization into Today/This Week/3-Month buckets in src/agents/catalyst_macro.py
- [X] T057 [US4] Implement macro dashboard (Fed Rate probability, DXY, Treasury, CPI/PCE) in src/agents/catalyst_macro.py
- [X] T058 [US4] Wire market_calendar tool for holiday detection in orchestrator in src/agents/orchestrator.py

### Tests for US4

- [X] T059 [P] [US4] Unit test for CatalystEvent time_bucket assignment in tests/unit/test_catalyst_event.py
- [X] T060 [P] [US4] Unit test for MacroIndicator trend calculation in tests/unit/test_macro_indicator.py
- [X] T061 [US4] Integration test for FRED API tool with mock responses in tests/integration/test_fred_tool.py

**Checkpoint**: US4 complete - Catalyst calendar and macro dashboard populated with categorized events

---

## Phase 7: User Story 5 - Metals Timing Advisor (Priority: P2)

**Goal**: Provide Gold/Silver timing advice weighted against DXY and Treasury yields per Constitution IV

**Independent Test**: Run MetalsAdvisor with various DXY/Treasury scenarios, verify recommendations align with correlation logic

### Data Models for US5

- [X] T062 [P] [US5] Create MetalsAdvice Pydantic model with required dxy_value, dxy_trend, treasury_10y, treasury_trend fields in src/models/metals_advice.py

### Agent Implementation for US5

- [X] T063 [US5] Implement MetalsAdvisorAgent with Gemini 3 Pro model in src/agents/metals_advisor.py
- [X] T064 [US5] Implement DXY correlation logic (accumulate on DXY strength) in src/agents/metals_advisor.py
- [X] T065 [US5] Implement Treasury yield context weighting in src/agents/metals_advisor.py
- [X] T066 [US5] Implement profit-taking logic (overbought + geopolitical tension) in src/agents/metals_advisor.py
- [X] T067 [US5] Wire MetalsAdvisorAgent to receive macro_context from CatalystMacroAgent in src/agents/orchestrator.py

### Tests for US5

- [X] T068 [P] [US5] Unit test for MetalsAdvice validation (dxy/treasury fields required) in tests/unit/test_metals_advisor.py
- [X] T069 [US5] Unit test for DXY correlation recommendation logic in tests/unit/test_metals_advisor.py
- [X] T070 [US5] Contract test for MetalsAdvice against JSON schema in tests/unit/test_metals_advisor.py

**Checkpoint**: US5 complete - Metals advisor provides recommendations with DXY/Treasury context per Constitution IV

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and final validation

- [X] T071 [P] Create README.md with project overview, setup instructions, GitHub Secrets documentation
- [X] T072 [P] Document API rate limits and caching strategy in README.md
- [X] T073 [P] Add inline code documentation for all Constitution rule implementations
- [X] T074 Run quickstart.md validation (follow local dev setup, verify working)
- [X] T075 Final integration test: run full pipeline end-to-end with real APIs (manual)
- [X] T076 Security review: verify no credentials in code, portfolio.json gitignored

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──────────────────────────────────────────────────────────┐
     │                                                                     │
     ▼                                                                     │
Phase 2 (Foundational) ─── BLOCKS ALL USER STORIES ───────────────────────┤
     │                                                                     │
     ├─────────────────────────────────────────────────────────────────────┤
     │                                                                     │
     ▼                                                                     │
Phase 3 (US1: Report Delivery) ← MVP ─────────────────────────────────────┤
     │                                                                     │
     ├──► Phase 4 (US2: Technical Scanner) [P1] ─────────────────────────┤
     │                                                                     │
     ├──► Phase 5 (US3: Portfolio Health) [P1] ──────────────────────────┤
     │                                                                     │
     ├──► Phase 6 (US4: Catalyst/Macro) [P2] ────────────────────────────┤
     │         │                                                           │
     │         ▼                                                           │
     └──► Phase 7 (US5: Metals Advisor) [P2] ← depends on US4 macro ─────┤
                                                                           │
Phase 8 (Polish) ← after desired stories complete ────────────────────────┘
```

### User Story Dependencies

| Story | Depends On | Can Parallelize With |
|-------|------------|----------------------|
| US1 (Report Delivery) | Foundational only | None (MVP base) |
| US2 (Technical Scanner) | Foundational + US1 shell | US3, US4 |
| US3 (Portfolio Health) | Foundational + US1 shell | US2, US4 |
| US4 (Catalyst/Macro) | Foundational + US1 shell | US2, US3 |
| US5 (Metals Advisor) | US4 (needs macro context) | None (depends on US4) |

### Parallel Opportunities Per Phase

**Phase 1 (Setup)**:
```
T003, T004, T005, T006 can run in parallel
```

**Phase 2 (Foundational)**:
```
T008, T009, T010 can run in parallel (after T007)
T011, T012 can run in parallel
```

**Phase 3 (US1)**:
```
T013, T014 can run in parallel (models)
T015 runs first (formatter), then T016, T017 can run in parallel (after T015)
T023, T024 can run in parallel (tests)
```

**Phase 4 (US2)**:
```
T026, T027 can run in parallel
T036, T037, T038 can run in parallel (tests)
```

**Phase 5 (US3)**:
```
T039, T040, T041 can run in parallel
T047, T048, T049 can run in parallel (tests)
```

**Phase 6 (US4)**:
```
T050, T051, T052, T053 can run in parallel
T059, T060 can run in parallel (tests)
```

**Phase 7 (US5)**:
```
T068 can run in parallel with implementation
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup → Project structure ready
2. Complete Phase 2: Foundational → Core utilities ready
3. Complete Phase 3: US1 → Report delivery working with placeholder data
4. **STOP and VALIDATE**: Manually trigger workflow, verify GitHub Issue + Telegram
5. Deploy if ready (basic infrastructure proven)

### Incremental Delivery (Recommended)

| Increment | Stories | Value Delivered |
|-----------|---------|-----------------|
| MVP | US1 | Report infrastructure, CI/CD pipeline |
| +1 | US1 + US2 | Technical breakout detection |
| +2 | US1 + US2 + US3 | Portfolio health monitoring |
| +3 | US1 + US2 + US3 + US4 | Catalyst calendar + macro dashboard |
| Complete | All 5 | Metals timing advisor |

### Parallel Team Strategy (if multiple developers)

```
Developer A: US1 (Report) → US4 (Catalyst/Macro) → US5 (Metals)
Developer B: US2 (Technical Scanner) → US3 (Portfolio Health)
```

Both start after Foundational phase completes.

---

## Task Summary

| Phase | Task Count | Parallel Tasks |
|-------|------------|----------------|
| 1. Setup | 6 | 4 |
| 2. Foundational | 6 | 4 |
| 3. US1 (Report) | 16 | 5 |
| 4. US2 (Scanner) | 13 | 4 |
| 5. US3 (Portfolio) | 11 | 5 |
| 6. US4 (Catalyst) | 12 | 6 |
| 7. US5 (Metals) | 9 | 2 |
| 8. Polish | 6 | 3 |
| **Total** | **79** | **33** |

### Constitution Compliance Mapping

| Constitution | Tasks Enforcing |
|--------------|-----------------|
| I. Financial Integrity | T026, T034, T036 |
| II. Data Governance | T027, T041, T053 |
| III. Risk Management (Biotech) | T033, T037 |
| III. Risk Management (Portfolio) | T044, T048 |
| IV. Macro Correlation | T064, T065, T069 |
| V. Operational Window | T021, T022 |

### Edge Case Handling (FR-028 to FR-030)

| Requirement | Task |
|-------------|------|
| FR-028 (Halted/delisted stocks) | T022a |
| FR-029 (Portfolio validation) | T022b |
| FR-030 (Telegram retry) | T022c |

---

## Notes

- All [P] tasks can run in parallel if assigned to different developers
- Models must be implemented before their consuming services
- Each user story checkpoint validates independent functionality
- Constitution rule implementations marked with inline comments
- Commit after each task or logical group
- Stop at any checkpoint to demo/validate progress
