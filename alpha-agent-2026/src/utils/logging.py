"""Structured logging utility for Alpha-Agent 2026.

Provides consistent logging format across all agents and tools.
"""

import logging
import sys
from datetime import datetime
from typing import Any


class AlphaAgentFormatter(logging.Formatter):
    """Custom formatter for Alpha-Agent logs.
    
    Format: [TIMESTAMP] [LEVEL] [COMPONENT] MESSAGE
    """
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        component = record.name.replace("src.", "").replace(".", "::")
        message = record.getMessage()
        
        if self.use_colors:
            color = self.COLORS.get(level, "")
            reset = self.COLORS["RESET"]
            return f"[{timestamp}] [{color}{level:8}{reset}] [{component}] {message}"
        
        return f"[{timestamp}] [{level:8}] [{component}] {message}"


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    use_colors: bool = True,
) -> None:
    """Configure logging for Alpha-Agent 2026.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        use_colors: Enable colored output for terminal (default: True)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with custom formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(AlphaAgentFormatter(use_colors=use_colors))
    root_logger.addHandler(console_handler)
    
    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(AlphaAgentFormatter(use_colors=False))
        root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific component.
    
    Args:
        name: Component name (e.g., 'agents.technical_scanner')
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger(__name__)
        logger.info("Starting technical scan...")
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding context to log messages.
    
    Example:
        with LogContext(logger, symbol="AAPL", agent="TechnicalScanner"):
            logger.info("Processing stock")
            # Output: [2026-01-15 08:00:00] [INFO] Processing stock [symbol=AAPL, agent=TechnicalScanner]
    """
    
    def __init__(self, logger: logging.Logger, **context: Any):
        self.logger = logger
        self.context = context
        self._original_factory: Any = None
    
    def __enter__(self) -> "LogContext":
        self._original_factory = logging.getLogRecordFactory()
        context = self.context
        
        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = self._original_factory(*args, **kwargs)
            if context:
                ctx_str = ", ".join(f"{k}={v}" for k, v in context.items())
                record.msg = f"{record.msg} [{ctx_str}]"
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, *args: Any) -> None:
        if self._original_factory:
            logging.setLogRecordFactory(self._original_factory)
