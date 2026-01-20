"""Configuration management for Alpha-Agent 2026.

Loads and validates environment variables required for pipeline execution.
All credentials are loaded from environment variables (never hardcoded).
"""

import os
from dataclasses import dataclass
from typing import ClassVar
from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment variables.
    
    Required environment variables:
        - ALPHA_VANTAGE_API_KEY: Stock data API key
        - FRED_API_KEY: Macro data API key
        - GEMINI_API_KEY: Google Gemini API key for LLM analysis
        - TELEGRAM_BOT_TOKEN: Telegram bot token
        - TELEGRAM_CHAT_ID: Telegram chat ID for notifications
    
    Optional environment variables:
        - GITHUB_TOKEN: GitHub API token (auto-provided in Actions)
        - GITHUB_REPOSITORY: Repository in format owner/repo
        - LOG_LEVEL: Logging level (default: INFO)
        - PIPELINE_TIMEOUT_MINUTES: Max pipeline runtime (default: 25)
        - PORTFOLIO_PATH: Path to portfolio.json (default: data/portfolio.json)
        - HOLIDAYS_PATH: Path to holidays JSON (default: data/nyse_holidays_2026.json)
    """
    
    # Required API keys
    alpha_vantage_api_key: str
    fred_api_key: str
    gemini_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    
    # Optional GitHub config
    github_token: str | None = None
    github_repository: str | None = None
    
    # Runtime config
    log_level: str = "INFO"
    pipeline_timeout_minutes: int = 25
    
    # Data paths
    portfolio_path: str = "data/portfolio.json"
    holidays_path: str = "data/nyse_holidays_2026.json"
    
    # Required fields for validation
    _REQUIRED_FIELDS: ClassVar[list[str]] = [
        "ALPHA_VANTAGE_API_KEY",
        "GEMINI_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]
    
    @classmethod
    def from_env(cls, env_file: str | None = None) -> "Config":
        """Load configuration from environment variables.
        
        Args:
            env_file: Optional path to .env file. If None, uses default .env
            
        Returns:
            Config instance with validated settings
            
        Raises:
            EnvironmentError: If required environment variables are missing
        """
        # Load .env file if it exists
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # Validate required fields
        missing = []
        for field in cls._REQUIRED_FIELDS:
            if not os.getenv(field):
                missing.append(field)
        
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please set them in your .env file or environment."
            )
        
        return cls(
            alpha_vantage_api_key=os.getenv("ALPHA_VANTAGE_API_KEY", ""),
            fred_api_key=os.getenv("FRED_API_KEY", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            github_token=os.getenv("GITHUB_TOKEN"),
            github_repository=os.getenv("GITHUB_REPOSITORY"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            pipeline_timeout_minutes=int(os.getenv("PIPELINE_TIMEOUT_MINUTES", "25")),
            portfolio_path=os.getenv("PORTFOLIO_PATH", "data/portfolio.json"),
            holidays_path=os.getenv("HOLIDAYS_PATH", "data/nyse_holidays_2026.json"),
        )
    
    def validate(self) -> bool:
        """Validate configuration values.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate API keys are not empty
        if not self.alpha_vantage_api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY cannot be empty")
        if not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN cannot be empty")
        if not self.telegram_chat_id:
            raise ValueError("TELEGRAM_CHAT_ID cannot be empty")
        
        # Validate timeout is reasonable
        if not 1 <= self.pipeline_timeout_minutes <= 60:
            raise ValueError("PIPELINE_TIMEOUT_MINUTES must be between 1 and 60")
        
        # Validate log level
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        
        return True
    
    @property
    def is_github_actions(self) -> bool:
        """Check if running in GitHub Actions environment."""
        return os.getenv("GITHUB_ACTIONS") == "true"
