"""GitHub Issue reporter for Alpha-Agent 2026.

Posts intelligence reports to GitHub Issues via the GitHub API.
Implements FR-024: Post comprehensive Markdown summary to GitHub Issue.
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from ..models.intelligence_report import IntelligenceReport
from ..utils.formatters import MarkdownFormatter
from ..utils.retry import with_retry

logger = logging.getLogger(__name__)


class GitHubIssueReporter:
    """Reports intelligence data to GitHub Issues.
    
    Creates a new issue for each daily report or updates an existing
    issue if one exists for today's date.
    """
    
    API_BASE = "https://api.github.com"
    
    def __init__(self, token: str, repository: str):
        """Initialize GitHub Issue reporter.
        
        Args:
            token: GitHub API token (PAT or GITHUB_TOKEN)
            repository: Repository in format 'owner/repo'
        """
        self.token = token
        self.repository = repository
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    async def post_report(self, report: IntelligenceReport) -> dict[str, Any]:
        """Post intelligence report as GitHub Issue.
        
        Args:
            report: IntelligenceReport to post
        
        Returns:
            Dict with issue URL and number
        
        Raises:
            httpx.HTTPError: If API request fails after retries
        """
        formatter = MarkdownFormatter(report)
        markdown = formatter.format()
        
        # Generate issue title with date
        date_str = report.generated_at.strftime("%Y-%m-%d")
        status_indicator = "✅" if report.is_complete else "⚠️" if report.is_partial else "🔒"
        title = f"{status_indicator} Alpha-Agent Daily Report - {date_str}"
        
        # Check for existing issue today
        existing = await self._find_todays_issue(date_str)
        
        if existing:
            logger.info(f"Updating existing issue #{existing['number']}")
            return await self._update_issue(existing["number"], markdown)
        else:
            logger.info("Creating new issue")
            return await self._create_issue(title, markdown)
    
    @with_retry(max_attempts=3, base_delay=1.0)
    async def _create_issue(self, title: str, body: str) -> dict[str, Any]:
        """Create a new GitHub issue.
        
        Args:
            title: Issue title
            body: Issue body (Markdown)
        
        Returns:
            Dict with issue details
        """
        url = f"{self.API_BASE}/repos/{self.repository}/issues"
        
        payload = {
            "title": title,
            "body": body,
            "labels": ["alpha-agent", "daily-report"],
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        
        logger.info(f"Created issue #{data['number']}: {data['html_url']}")
        
        return {
            "number": data["number"],
            "url": data["html_url"],
            "created": True,
        }
    
    @with_retry(max_attempts=3, base_delay=1.0)
    async def _update_issue(self, issue_number: int, body: str) -> dict[str, Any]:
        """Update an existing GitHub issue.
        
        Args:
            issue_number: Issue number to update
            body: New issue body (Markdown)
        
        Returns:
            Dict with issue details
        """
        url = f"{self.API_BASE}/repos/{self.repository}/issues/{issue_number}"
        
        payload = {"body": body}
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                headers=self.headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        
        logger.info(f"Updated issue #{data['number']}: {data['html_url']}")
        
        return {
            "number": data["number"],
            "url": data["html_url"],
            "created": False,
        }
    
    async def _find_todays_issue(self, date_str: str) -> dict[str, Any] | None:
        """Find existing issue for today's date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        
        Returns:
            Issue data if found, None otherwise
        """
        url = f"{self.API_BASE}/repos/{self.repository}/issues"
        params = {
            "labels": "alpha-agent,daily-report",
            "state": "open",
            "per_page": 10,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                issues = response.json()
            
            for issue in issues:
                if date_str in issue.get("title", ""):
                    return issue
            
            return None
        
        except httpx.HTTPError as e:
            logger.warning(f"Failed to search for existing issues: {e}")
            return None
