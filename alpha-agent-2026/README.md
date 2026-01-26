# Alpha-Agent 2026

> Multi-Agent Investment Intelligence Ecosystem

A production-grade AI-powered investment intelligence system that delivers daily actionable insights via GitHub Issues, implementing the Alpha-Agent 2026 Constitution principles.

## 🏛️ Constitution Principles

This system operates under five foundational principles:

1. **Constitution I - Financial Integrity**: Every trade recommendation includes entry price, target, and 2.5% trailing stop-loss
2. **Constitution II - Data Governance**: Read-only data access via MCP (Model Context Protocol)
3. **Constitution III - Risk Management**: $500M biotech filter, Option B exit/hedge logic for positions >10% or loss >10%
4. **Constitution IV - Macro Correlation**: DXY correlation mandatory for GLD recommendations
5. **Constitution V - Operational Window**: 08:00 AM EST delivery, NYSE holiday awareness

## 🤖 Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  AlphaAgentOrchestrator                     │
│              (Google ADK SequentialAgent)                   │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Technical    │  │   Portfolio   │  │   Catalyst    │
│   Scanner     │  │   Analyst     │  │    Macro      │
│ (Gemini Flash)│  │ (Gemini Pro)  │  │ (Gemini Pro)  │
└───────────────┘  └───────────────┘  └───────────────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Alpha Vantage │  │    News       │  │    FRED       │
│     MCP       │  │  Sentiment    │  │    API        │
└───────────────┘  └───────────────┘  └───────────────┘
                           │
                           ▼
                 ┌───────────────┐
                 │    Metals     │
                 │   Advisor     │
                 │ (Gemini Pro)  │
                 └───────────────┘
```

## 📦 Installation

### Prerequisites

- Python 3.11+
- API Keys:
  - Google AI (Gemini API)
  - Alpha Vantage
  - FRED
  - Telegram Bot Token
  - GitHub Token (for issue creation)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/alpha-agent-2026.git
cd alpha-agent-2026

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```env
# Required
GOOGLE_AI_API_KEY=your_gemini_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
FRED_API_KEY=your_fred_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id
GITHUB_TOKEN=your_github_token
GITHUB_REPO=owner/repo

# Optional
LOG_LEVEL=INFO
DRY_RUN=false
```

## 🚀 Usage

### Daily Scan (Manual)

```bash
# Full scan with GitHub issue delivery
python -m src.main --scan

# Dry run (no external API calls)
python -m src.main --scan --dry-run

# Specific universe
python -m src.main --scan --universe TECH_LEADERS
```

### Automated Delivery

The system runs automatically via GitHub Actions at 08:00 AM EST (13:00 UTC) on trading days.

See [.github/workflows/daily_scan.yml](.github/workflows/daily_scan.yml)

## 📊 Output Format

### Intelligence Report

Each daily report includes:

1. **Technical Signals** (max 10 recommendations)
   - RSI crossover alerts
   - Volume spike detection
   - Entry/Target/Stop-loss levels

2. **Portfolio Health**
   - Position vs 20-day SMA
   - Exit/Hedge signals (Option B logic)
   - Top-up opportunities

3. **Catalyst Calendar**
   - TODAY: Immediate action items
   - THIS_WEEK: Near-term events
   - THREE_MONTH: Strategic planning

4. **Macro Dashboard**
   - DXY index and trend
   - Treasury 10Y yield
   - CPI/PCE inflation data

5. **Metals Advice**
   - GLD recommendation with DXY correlation
   - Treasury yield weighting

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_technical_scanner.py

# Run integration tests
pytest tests/integration/
```

## 📁 Project Structure

```
alpha-agent-2026/
├── src/
│   ├── agents/           # AI Agents
│   │   ├── orchestrator.py
│   │   ├── technical_scanner.py
│   │   ├── portfolio_analyst.py
│   │   ├── catalyst_macro.py
│   │   └── metals_advisor.py
│   ├── models/           # Pydantic Models
│   │   ├── trade_recommendation.py
│   │   ├── portfolio_holding.py
│   │   ├── catalyst_event.py
│   │   ├── macro_indicator.py
│   │   ├── metals_advice.py
│   │   └── intelligence_report.py
│   ├── tools/            # MCP Data Tools
│   │   ├── alpha_vantage.py
│   │   ├── portfolio_reader.py
│   │   ├── fred_data.py
│   │   ├── news_sentiment.py
│   │   └── market_calendar.py
│   ├── delivery/         # Output Channels
│   │   ├── github_issue.py
│   │   └── telegram_bot.py
│   └── utils/            # Utilities
│       ├── config.py
│       ├── logging.py
│       ├── retry.py
│       └── formatters.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── data/
│   ├── portfolio.example.json
│   └── nyse_holidays_2026.json
└── .github/
    └── workflows/
        └── daily_scan.yml
```

## 🔒 Security

- **No Secrets in Code**: All credentials via environment variables
- **Read-Only Data Access**: MCP tools cannot modify external systems
- **Portfolio Data**: `portfolio.json` is gitignored
- **Rate Limiting**: Built-in API rate limiting and caching

## 📝 API Rate Limits

| Service | Limit | Caching |
|---------|-------|---------|
| Alpha Vantage | 5 calls/min (free), 75/min (premium) | 15 minutes |
| FRED | 120 requests/minute | 24 hours |
| Telegram | 30 messages/second | None |
| GitHub | 5000 requests/hour | None |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Google AI (Gemini)
- Alpha Vantage
- Federal Reserve Economic Data (FRED)
- MCP Protocol

---

**⚠️ Disclaimer**: This system provides investment intelligence for informational purposes only. It does not constitute financial advice. Always conduct your own research and consult with a qualified financial advisor before making investment decisions.
