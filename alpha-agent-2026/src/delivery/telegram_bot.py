"""Telegram bot notifier for Alpha-Agent 2026.

Sends mobile notifications via Telegram Bot API.
Implements FR-025: Mobile-friendly notification with report summary (≤280 chars).
Implements FR-030: Retry queue (3 attempts) for failed deliveries.
"""

import asyncio
import logging
from typing import Any

import httpx

from ..models.intelligence_report import IntelligenceReport
from ..utils.formatters import MarkdownFormatter
from ..utils.retry import with_retry, RetryExhausted

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends notifications via Telegram Bot API.
    
    Implements FR-025 and FR-030 for mobile notification delivery
    with retry capability.
    """
    
    API_BASE = "https://api.telegram.org"
    MAX_MESSAGE_LENGTH = 280  # FR-025: ≤280 chars
    
    def __init__(self, bot_token: str, chat_id: str):
        """Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Target chat ID for notifications
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._retry_queue: list[dict[str, Any]] = []
    
    async def send_report_notification(
        self,
        report: IntelligenceReport,
        issue_url: str | None = None,
    ) -> bool:
        """Send notification for intelligence report.
        
        Args:
            report: IntelligenceReport to summarize
            issue_url: Optional URL to full GitHub Issue
        
        Returns:
            True if notification sent successfully
        """
        formatter = MarkdownFormatter(report)
        summary = formatter.format_summary(max_length=self.MAX_MESSAGE_LENGTH - 50)  # Reserve space for link
        
        # Append issue link if provided
        if issue_url:
            summary = f"{summary}\n\n🔗 [View Full Report]({issue_url})"
        
        return await self._send_with_retry(summary)
    
    async def send_market_closed_notification(self, holiday_name: str | None = None) -> bool:
        """Send market closed notification.
        
        Args:
            holiday_name: Optional name of the holiday
        
        Returns:
            True if notification sent successfully
        """
        message = "🔒 **Market Closed Today**"
        if holiday_name:
            message += f"\n\n📅 {holiday_name}"
        message += "\n\nNo trading report available."
        
        return await self._send_with_retry(message)
    
    async def _send_with_retry(self, message: str) -> bool:
        """Send message with retry logic (FR-030).
        
        Args:
            message: Message text to send
        
        Returns:
            True if sent successfully, False if all retries failed
        """
        try:
            await self._send_message(message)
            return True
        except RetryExhausted as e:
            logger.error(f"Telegram notification failed after retries: {e}")
            # FR-030: Log error but do not fail the pipeline
            self._retry_queue.append({
                "message": message,
                "error": str(e),
                "attempts": 3,
            })
            return False
    
    @with_retry(max_attempts=3, base_delay=2.0)
    async def _send_message(self, text: str) -> dict[str, Any]:
        """Send message via Telegram API.
        
        Args:
            text: Message text (Markdown supported)
        
        Returns:
            API response data
        
        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.API_BASE}/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        
        if not data.get("ok"):
            raise httpx.HTTPError(f"Telegram API error: {data.get('description', 'Unknown')}")
        
        logger.info(f"Telegram notification sent to chat {self.chat_id}")
        return data
    
    async def process_retry_queue(self) -> int:
        """Process any queued failed notifications.
        
        Returns:
            Number of successfully sent queued messages
        """
        if not self._retry_queue:
            return 0
        
        sent = 0
        remaining = []
        
        for item in self._retry_queue:
            try:
                await self._send_message(item["message"])
                sent += 1
                logger.info("Successfully sent queued notification")
            except Exception as e:
                logger.warning(f"Queued notification still failing: {e}")
                remaining.append(item)
        
        self._retry_queue = remaining
        return sent
    
    @property
    def has_queued_failures(self) -> bool:
        """Check if there are queued failed notifications."""
        return len(self._retry_queue) > 0
