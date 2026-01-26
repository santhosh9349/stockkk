"""Retry decorator with exponential backoff for Alpha-Agent 2026.

Implements FR-026: Retry failed data source requests with exponential backoff
(up to 3 attempts), then proceed with available data.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, TypeVar, ParamSpec

P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)


class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted."""
    
    def __init__(self, func_name: str, attempts: int, last_error: Exception):
        self.func_name = func_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Function '{func_name}' failed after {attempts} attempts. "
            f"Last error: {last_error}"
        )


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for retrying async functions with exponential backoff.
    
    Implements Constitution compliance for FR-026: System MUST retry failed
    data source requests with exponential backoff (up to 3 attempts).
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3 per FR-026)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 30.0)
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback called before each retry (attempt_num, exception)
    
    Returns:
        Decorated function that retries on failure
    
    Example:
        @with_retry(max_attempts=3, base_delay=1.0)
        async def fetch_stock_data(symbol: str) -> dict:
            # API call that might fail
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"[RETRY] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise RetryExhausted(func.__name__, max_attempts, e) from e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    
                    logger.warning(
                        f"[RETRY] {func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    # Call optional retry callback
                    if on_retry:
                        on_retry(attempt, e)
                    
                    await asyncio.sleep(delay)
            
            # This should never be reached, but satisfy type checker
            raise RetryExhausted(func.__name__, max_attempts, last_exception or Exception("Unknown"))
        
        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"[RETRY] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise RetryExhausted(func.__name__, max_attempts, e) from e
                    
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    
                    logger.warning(
                        f"[RETRY] {func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    import time
                    time.sleep(delay)
            
            raise RetryExhausted(func.__name__, max_attempts, last_exception or Exception("Unknown"))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator
