"""Markdown report formatter for Alpha-Agent 2026.

Generates formatted Markdown reports from IntelligenceReport data
for posting to GitHub Issues.
"""

from datetime import datetime
from typing import Any

from ..models.intelligence_report import IntelligenceReport, DataUnavailable
from ..models import ReportStatus


class MarkdownFormatter:
    """Formats IntelligenceReport as Markdown for GitHub Issues."""
    
    HEADER_TEMPLATE = """# 📊 Alpha-Agent Daily Intelligence Report

**Generated**: {timestamp}  
**Status**: {status_emoji} {status}

---

"""
    
    MARKET_CLOSED_TEMPLATE = """# 📊 Alpha-Agent Daily Intelligence Report

**Generated**: {timestamp}  
**Status**: 🔒 Market Closed

---

## 🏖️ Market Holiday Notice

The market is closed today{holiday_reason}.

No trading analysis available. The next report will be generated on the next trading day.

---

*Alpha-Agent 2026 - Automated Investment Intelligence*
"""
    
    FOOTER_TEMPLATE = """
---

*Alpha-Agent 2026 - Automated Investment Intelligence*  
*Generated at {timestamp} EST*
"""
    
    def __init__(self, report: IntelligenceReport):
        """Initialize formatter with report data.
        
        Args:
            report: IntelligenceReport to format
        """
        self.report = report
    
    def format(self) -> str:
        """Generate complete Markdown report.
        
        Returns:
            Formatted Markdown string
        """
        if self.report.is_market_closed:
            return self._format_market_closed()
        
        sections = [
            self._format_header(),
            self._format_unavailable_notice(),
            self._format_technical_scans(),
            self._format_portfolio_alerts(),
            self._format_catalysts(),
            self._format_macro_dashboard(),
            self._format_metals_advice(),
            self._format_footer(),
        ]
        
        return "\n".join(filter(None, sections))
    
    def format_summary(self, max_length: int = 280) -> str:
        """Generate summary for Telegram notification (FR-025: ≤280 chars).
        
        Args:
            max_length: Maximum character length (default: 280)
        
        Returns:
            Brief summary string
        """
        if self.report.is_market_closed:
            return f"🔒 Market Closed{' - ' + self.report.holiday_name if self.report.holiday_name else ''}"
        
        stats = self.report.get_summary_stats()
        
        summary_parts = [
            f"📊 Alpha-Agent Report",
            f"📈 {stats['technical_scans']} breakouts",
            f"💼 {stats['portfolio_alerts']} alerts",
            f"📅 {stats['catalysts']} catalysts",
        ]
        
        if stats['unavailable_sections'] > 0:
            summary_parts.append(f"⚠️ {stats['unavailable_sections']} sections unavailable")
        
        summary = " | ".join(summary_parts)
        
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."
        
        return summary
    
    def _format_header(self) -> str:
        """Format report header."""
        status_emojis = {
            ReportStatus.COMPLETE: "✅",
            ReportStatus.PARTIAL: "⚠️",
            ReportStatus.MARKET_CLOSED: "🔒",
        }
        
        return self.HEADER_TEMPLATE.format(
            timestamp=self.report.generated_at.strftime("%Y-%m-%d %H:%M EST"),
            status_emoji=status_emojis.get(self.report.status, "❓"),
            status=self.report.status.value,
        )
    
    def _format_unavailable_notice(self) -> str:
        """Format notice for unavailable sections."""
        if not self.report.unavailable_sections:
            return ""
        
        sections_list = ", ".join(self.report.unavailable_sections)
        return f"""## ⚠️ Data Availability Notice

Some data sources were unavailable: **{sections_list}**

The report continues with available data.

---

"""
    
    def _format_technical_scans(self) -> str:
        """Format technical scanner results."""
        if not self.report.technical_scans:
            if "technical_scans" in self.report.unavailable_sections:
                return "## 📈 Technical Breakouts\n\n*Data unavailable*\n"
            return "## 📈 Technical Breakouts\n\n*No breakout candidates detected*\n"
        
        lines = ["## 📈 Technical Breakouts\n"]
        lines.append("| Symbol | Universe | Entry | Target | Stop-Loss | RSI | Confidence |")
        lines.append("|--------|----------|-------|--------|-----------|-----|------------|")
        
        for rec in self.report.technical_scans[:10]:  # FR-009: Top 10 limit
            if isinstance(rec, dict):
                lines.append(
                    f"| {rec.get('symbol', 'N/A')} "
                    f"| {rec.get('universe', 'N/A')} "
                    f"| ${rec.get('entry', 0):.2f} "
                    f"| ${rec.get('target', 0):.2f} "
                    f"| ${rec.get('stop_loss', 0):.2f} "
                    f"| {rec.get('rsi', 0):.1f} "
                    f"| {rec.get('confidence', 0):.0%} |"
                )
            else:
                # Pydantic model
                lines.append(
                    f"| {rec.symbol} "
                    f"| {rec.universe.value} "
                    f"| ${rec.entry:.2f} "
                    f"| ${rec.target:.2f} "
                    f"| ${rec.stop_loss:.2f} "
                    f"| {rec.rsi:.1f} "
                    f"| {rec.confidence:.0%} |"
                )
        
        lines.append("")
        return "\n".join(lines)
    
    def _format_portfolio_alerts(self) -> str:
        """Format portfolio health alerts."""
        if not self.report.portfolio_alerts:
            if "portfolio_alerts" in self.report.unavailable_sections:
                return "## 💼 Portfolio Health\n\n*Data unavailable*\n"
            return "## 💼 Portfolio Health\n\n*All holdings are healthy*\n"
        
        lines = ["## 💼 Portfolio Health\n"]
        lines.append("| Symbol | Signal | vs SMA | P&L | Rationale |")
        lines.append("|--------|--------|--------|-----|-----------|")
        
        for alert in self.report.portfolio_alerts:
            if isinstance(alert, dict):
                signal_emoji = {"EXIT": "🔴", "HEDGE": "🟡", "TOP_UP": "🟢", "HOLD": "⚪"}.get(
                    alert.get("signal", "HOLD"), "⚪"
                )
                lines.append(
                    f"| {alert.get('symbol', 'N/A')} "
                    f"| {signal_emoji} {alert.get('signal', 'N/A')} "
                    f"| {alert.get('pct_vs_sma', 0):+.1f}% "
                    f"| {alert.get('pnl_pct', 0):+.1f}% "
                    f"| {alert.get('rationale', 'N/A')[:30]}... |"
                )
        
        lines.append("")
        return "\n".join(lines)
    
    def _format_catalysts(self) -> str:
        """Format catalyst calendar."""
        if not self.report.catalysts:
            if "catalysts" in self.report.unavailable_sections:
                return "## 📅 Catalyst Calendar\n\n*Data unavailable*\n"
            return "## 📅 Catalyst Calendar\n\n*No upcoming catalysts*\n"
        
        lines = ["## 📅 Catalyst Calendar\n"]
        
        # Group by time bucket
        buckets: dict[str, list[Any]] = {"TODAY": [], "THIS_WEEK": [], "THREE_MONTH": []}
        for event in self.report.catalysts:
            bucket = event.get("time_bucket", "THREE_MONTH") if isinstance(event, dict) else event.time_bucket.value
            if bucket in buckets:
                buckets[bucket].append(event)
        
        bucket_headers = {
            "TODAY": "### 🔥 Today",
            "THIS_WEEK": "### 📆 This Week",
            "THREE_MONTH": "### 🗓️ 3-Month Horizon",
        }
        
        for bucket, events in buckets.items():
            if events:
                lines.append(bucket_headers[bucket])
                for event in events:
                    if isinstance(event, dict):
                        lines.append(f"- **{event.get('event_type', 'EVENT')}**: {event.get('description', 'N/A')}")
                    else:
                        lines.append(f"- **{event.event_type.value}**: {event.description}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_macro_dashboard(self) -> str:
        """Format macro indicators dashboard."""
        if not self.report.macro_indicators:
            if "macro_indicators" in self.report.unavailable_sections:
                return "## 📊 Macro Dashboard\n\n*Data unavailable*\n"
            return "## 📊 Macro Dashboard\n\n*No macro data available*\n"
        
        lines = ["## 📊 Macro Dashboard\n"]
        lines.append("| Indicator | Value | Trend |")
        lines.append("|-----------|-------|-------|")
        
        trend_emojis = {"STRENGTHENING": "📈", "WEAKENING": "📉", "NEUTRAL": "➡️"}
        
        for indicator in self.report.macro_indicators:
            if isinstance(indicator, dict):
                trend = indicator.get("trend", "NEUTRAL")
                lines.append(
                    f"| {indicator.get('name', 'N/A')} "
                    f"| {indicator.get('value', 'N/A')} "
                    f"| {trend_emojis.get(trend, '➡️')} {trend} |"
                )
        
        lines.append("")
        return "\n".join(lines)
    
    def _format_metals_advice(self) -> str:
        """Format metals advisor section."""
        if not self.report.metals_advice:
            if "metals_advice" in self.report.unavailable_sections:
                return "## 🥇 Metals Advisor\n\n*Data unavailable*\n"
            return "## 🥇 Metals Advisor\n\n*No metals recommendation*\n"
        
        advice = self.report.metals_advice
        lines = ["## 🥇 Metals Advisor\n"]
        
        if isinstance(advice, dict):
            action_emojis = {"ACCUMULATE": "💰", "PROFIT_TAKE": "💵", "HOLD": "⏸️"}
            gld_action = advice.get("gld_action", "HOLD")
            slv_action = advice.get("slv_action", "HOLD")
            
            lines.append(f"**Gold (GLD)**: {action_emojis.get(gld_action, '⏸️')} {gld_action}")
            lines.append(f"**Silver (SLV)**: {action_emojis.get(slv_action, '⏸️')} {slv_action}")
            lines.append("")
            lines.append(f"**DXY**: {advice.get('dxy_value', 'N/A')} ({advice.get('dxy_trend', 'N/A')})")
            lines.append(f"**10Y Treasury**: {advice.get('treasury_10y', 'N/A')}% ({advice.get('treasury_trend', 'N/A')})")
            lines.append("")
            lines.append(f"**Rationale**: {advice.get('rationale', 'N/A')}")
        
        lines.append("")
        return "\n".join(lines)
    
    def _format_market_closed(self) -> str:
        """Format market closed notice."""
        holiday_reason = ""
        if self.report.holiday_name:
            holiday_reason = f" ({self.report.holiday_name})"
        
        return self.MARKET_CLOSED_TEMPLATE.format(
            timestamp=self.report.generated_at.strftime("%Y-%m-%d %H:%M EST"),
            holiday_reason=holiday_reason,
        )
    
    def _format_footer(self) -> str:
        """Format report footer."""
        return self.FOOTER_TEMPLATE.format(
            timestamp=self.report.generated_at.strftime("%Y-%m-%d %H:%M"),
        )
