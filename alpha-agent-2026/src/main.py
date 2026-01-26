"""Alpha-Agent 2026 CLI entry point.

Provides command-line interface for running the investment intelligence pipeline.
Implements FR-022 (daily trigger) and FR-027 (market-closed mode).
"""

import argparse
import asyncio
import json
import sys
from datetime import date, datetime
from pathlib import Path

from .agents.orchestrator import AlphaAgentOrchestrator
from .delivery.github_issue import GitHubIssueReporter
from .delivery.telegram_bot import TelegramNotifier
from .utils.config import Config
from .utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


def load_holidays(holidays_path: str) -> list[str]:
    """Load NYSE holiday calendar.
    
    Args:
        holidays_path: Path to holidays JSON file
    
    Returns:
        List of holiday dates in YYYY-MM-DD format
    """
    try:
        with open(holidays_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Holiday calendar not found: {holidays_path}")
        return []


def is_market_holiday(holidays: list[str], check_date: date | None = None) -> tuple[bool, str | None]:
    """Check if given date is a market holiday.
    
    Args:
        holidays: List of holiday dates
        check_date: Date to check (default: today)
    
    Returns:
        Tuple of (is_holiday, holiday_name)
    """
    if check_date is None:
        check_date = date.today()
    
    date_str = check_date.strftime("%Y-%m-%d")
    
    # Simple check - more sophisticated would include holiday names
    if date_str in holidays:
        return True, f"NYSE Holiday ({date_str})"
    
    # Check if weekend
    if check_date.weekday() >= 5:
        return True, "Weekend"
    
    return False, None


async def run_pipeline(args: argparse.Namespace) -> int:
    """Run the Alpha-Agent pipeline.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Load configuration
    try:
        config = Config.from_env()
        config.validate()
    except EnvironmentError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    
    # Check for market holidays (FR-027)
    holidays = load_holidays(config.holidays_path)
    is_holiday, holiday_name = is_market_holiday(holidays)
    
    # Override with --market-closed flag
    market_closed = args.market_closed or is_holiday
    
    if market_closed and not args.market_closed:
        logger.info(f"Market is closed: {holiday_name}")
    
    # Initialize orchestrator
    orchestrator = AlphaAgentOrchestrator(config)
    
    # Run pipeline
    report = await orchestrator.run(market_closed=market_closed)
    
    # Handle output
    issue_url = None
    
    if args.output == "console":
        # Just log the report
        from .utils.formatters import MarkdownFormatter
        formatter = MarkdownFormatter(report)
        print(formatter.format())
        
    elif args.output == "github-issue":
        # Post to GitHub Issue (FR-024)
        if not config.github_token or not config.github_repository:
            logger.error("GitHub output requires GITHUB_TOKEN and GITHUB_REPOSITORY")
            return 1
        
        reporter = GitHubIssueReporter(config.github_token, config.github_repository)
        result = await reporter.post_report(report)
        issue_url = result.get("url")
        logger.info(f"Report posted to: {issue_url}")
    
    # Send notification (FR-025)
    if args.notify == "telegram":
        notifier = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
        
        if market_closed:
            await notifier.send_market_closed_notification(holiday_name)
        else:
            await notifier.send_report_notification(report, issue_url)
    
    return 0


def main() -> None:
    """Main entry point for Alpha-Agent CLI."""
    parser = argparse.ArgumentParser(
        description="Alpha-Agent 2026 - Multi-Agent Investment Intelligence System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                           # Run pipeline, output to console
  python -m src.main --output github-issue     # Post to GitHub Issue
  python -m src.main --notify telegram         # Send Telegram notification
  python -m src.main --market-closed           # Post market closed notice
        """,
    )
    
    parser.add_argument(
        "--output",
        choices=["console", "github-issue"],
        default="console",
        help="Output destination (default: console)",
    )
    
    parser.add_argument(
        "--notify",
        choices=["none", "telegram"],
        default="none",
        help="Notification channel (default: none)",
    )
    
    parser.add_argument(
        "--market-closed",
        action="store_true",
        help="Force market closed mode (skip agents)",
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Run pipeline
    try:
        exit_code = asyncio.run(run_pipeline(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
