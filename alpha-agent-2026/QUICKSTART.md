# Quickstart Guide

Get Alpha-Agent 2026 running locally in under 5 minutes.

## Prerequisites

- Python 3.11 or higher
- Git
- API Keys (see below)

## Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/alpha-agent-2026.git
cd alpha-agent-2026

# Create virtual environment
python -m venv .venv

# Activate (choose your OS)
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required APIs
GOOGLE_AI_API_KEY=your_gemini_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
FRED_API_KEY=your_fred_key_here

# Delivery channels
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id
GITHUB_TOKEN=your_github_token
GITHUB_REPO=owner/repo

# Optional
LOG_LEVEL=INFO
DRY_RUN=false
```

### Getting API Keys

1. **Google AI (Gemini)**: [Google AI Studio](https://aistudio.google.com/)
2. **Alpha Vantage**: [Alpha Vantage](https://www.alphavantage.co/support/#api-key) (free tier available)
3. **FRED**: [FRED API](https://fred.stlouisfed.org/docs/api/api_key.html)
4. **Telegram Bot**: [BotFather](https://t.me/botfather)
5. **GitHub Token**: [Personal Access Tokens](https://github.com/settings/tokens)

## Step 3: Run in Dry-Run Mode

Test the system without making real API calls:

```bash
python -m src.main --scan --dry-run
```

Expected output:
```
INFO: Starting Alpha-Agent pipeline...
INFO: Running Technical Scanner...
INFO: Technical Scanner found 2 candidates
INFO: Running Portfolio Analyst...
INFO: Portfolio Analyst generated 1 alerts
INFO: Running Catalyst & Macro Agent...
INFO: Catalyst Agent found 1 events
INFO: Running Metals Advisor...
INFO: Metals Advisor generated recommendation
INFO: Pipeline completed in 0.5s - Status: COMPLETE
```

## Step 4: Run with Real APIs

Once configured, run the full pipeline:

```bash
python -m src.main --scan
```

This will:
1. Scan your configured universes (QQQ, IBB, ITA, SPY)
2. Analyze your portfolio (from `data/portfolio.json`)
3. Check upcoming catalysts and macro indicators
4. Generate metals timing advice
5. Create a GitHub Issue with the report
6. Send a Telegram notification

## Step 5: Set Up Portfolio (Optional)

Create your portfolio file:

```bash
cp data/portfolio.example.json data/portfolio.json
```

Edit `data/portfolio.json` with your actual holdings:

```json
{
  "holdings": [
    {
      "ticker": "AAPL",
      "shares": 100,
      "avg_cost": 150.00
    },
    {
      "ticker": "MSFT",
      "shares": 50,
      "avg_cost": 380.00
    }
  ],
  "last_updated": "2026-01-15"
}
```

## Step 6: Run Tests

Verify everything is working:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_technical_scanner.py -v
```

## Troubleshooting

### Common Issues

1. **API Rate Limits**
   - Alpha Vantage free tier: 5 calls/minute
   - Use `--dry-run` during development

2. **Import Errors**
   - Ensure you're in the virtual environment
   - Reinstall: `pip install -e .`

3. **Telegram Not Working**
   - Verify bot token is correct
   - Ensure bot is added to channel as admin

4. **No GitHub Issue Created**
   - Check GITHUB_TOKEN has `repo` scope
   - Verify GITHUB_REPO format: `owner/repo`

### Debug Mode

Enable verbose logging:

```bash
LOG_LEVEL=DEBUG python -m src.main --scan --dry-run
```

## Next Steps

- [README.md](README.md) - Full documentation
- [Constitution](docs/constitution.md) - System principles
- [Architecture](docs/architecture.md) - Technical design

---

**Questions?** Open an issue on GitHub.
