# Quickstart: Alpha-Agent 2026

Get the Multi-Agent Investment Ecosystem running locally in 5 minutes.

---

## Prerequisites

- Python 3.11+
- Git
- API Keys:
  - Alpha Vantage (free tier: https://www.alphavantage.co/support/#api-key)
  - FRED (free: https://fred.stlouisfed.org/docs/api/api_key.html)
  - Telegram Bot Token (via @BotFather)

---

## 1. Clone & Setup

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/alpha-agent-2026.git
cd alpha-agent-2026

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API keys
```

**.env contents:**
```ini
ALPHA_VANTAGE_API_KEY=your_key_here
FRED_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## 3. Setup Portfolio Data

```bash
# Copy example portfolio
cp data/portfolio.example.json data/portfolio.json

# Edit with your actual holdings
```

**data/portfolio.json:**
```json
{
  "holdings": [
    {"symbol": "AAPL", "shares": 100, "cost_basis": 150.00, "entry_date": "2025-06-15"},
    {"symbol": "NVDA", "shares": 50, "cost_basis": 450.00, "entry_date": "2025-08-01"}
  ],
  "last_updated": "2026-01-14T08:00:00Z"
}
```

---

## 4. Run Locally

```bash
# Full pipeline (outputs to console)
python -m src.main

# With GitHub Issue output
python -m src.main --output github-issue

# With Telegram notification
python -m src.main --output github-issue --notify telegram

# Market closed notice (for testing)
python -m src.main --market-closed
```

---

## 5. Run Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# With coverage
pytest --cov=src --cov-report=html
```

---

## 6. Setup GitHub Actions (Production)

### Required Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret Name | Description |
|-------------|-------------|
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key |
| `FRED_API_KEY` | FRED API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `PORTFOLIO_JSON_BASE64` | Base64-encoded portfolio.json |

### Encode Portfolio for Secret

```bash
# Encode your portfolio file
base64 -w 0 data/portfolio.json > portfolio.b64
cat portfolio.b64  # Copy this output to PORTFOLIO_JSON_BASE64 secret
```

### Manual Trigger

Go to **Actions → Alpha-Agent Daily Scan → Run workflow** to test.

---

## Project Structure

```
alpha-agent-2026/
├── src/
│   ├── main.py              # Entry point
│   ├── agents/              # Google ADK agents
│   ├── tools/               # MCP tools (read-only)
│   ├── models/              # Pydantic models
│   ├── utils/               # Helpers (config, retry, logging)
│   └── delivery/            # GitHub Issue, Telegram
├── tests/
├── data/
│   ├── portfolio.example.json
│   └── nyse_holidays_2026.json
├── .github/workflows/
│   └── daily_scan.yml
└── requirements.txt
```

---

## Troubleshooting

### "Rate limit exceeded" from Alpha Vantage
- Free tier: 5 calls/min, 500/day
- Solution: Wait 1 minute, or upgrade to premium

### "Market holiday" notice when market is open
- Check `data/nyse_holidays_2026.json` is accurate
- Verify system timezone is correct

### Telegram notification not received
1. Verify bot token with: `curl https://api.telegram.org/bot<TOKEN>/getMe`
2. Verify chat ID with: `curl https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Ensure you've started a chat with the bot

### GitHub Action times out
- Default timeout: 30 minutes
- Check Alpha Vantage rate limits aren't causing delays
- Review action logs for stuck API calls

---

## Next Steps

1. **Customize scan universes**: Edit `src/agents/technical_scanner.py`
2. **Adjust risk parameters**: Modify thresholds in `src/agents/portfolio_analyst.py`
3. **Add new data sources**: Implement additional tools in `src/tools/`
4. **Backtest strategies**: (Out of scope for v1, but structure supports it)
