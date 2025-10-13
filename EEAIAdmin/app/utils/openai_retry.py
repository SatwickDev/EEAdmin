"""
OpenAI Retry Mechanism with Exponential Backoff
Handles rate limits and transient errors for OpenAI API calls
"""

import logging
import time
import functools
import re
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

# Import OpenAI errors with compatibility for different versions
try:
    # Try new OpenAI package structure (v1.0+)
    from openai import RateLimitError, APIError, APIConnectionError, Timeout
except ImportError:
    # Fallback to older OpenAI package structure (v0.x)
    try:
        import openai.error as openai_error
        RateLimitError = openai_error.RateLimitError
        APIError = openai_error.APIError
        APIConnectionError = openai_error.APIConnectionError
        Timeout = openai_error.Timeout
    except (ImportError, AttributeError):
        # If imports fail, create placeholder exceptions
        logger.warning("Could not import OpenAI error classes, using generic Exception")
        RateLimitError = Exception
        APIError = Exception
        APIConnectionError = Exception
        Timeout = Exception


class OpenAIRetryConfig:
    """Configuration for OpenAI retry mechanism"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry configuration

        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay in seconds (default: 60.0)
            exponential_base: Base for exponential backoff (default: 2.0)
            jitter: Add random jitter to delays (default: True)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def extract_retry_after(error_message: str) -> Optional[float]:
    """
    Extract retry-after time from Azure OpenAI error message

    Args:
        error_message: Error message from Azure OpenAI

    Returns:
        Number of seconds to wait, or None if not found
    """
    # Pattern for "Please retry after X seconds"
    pattern = r"retry after (\d+(?:\.\d+)?)\s*second"
    match = re.search(pattern, str(error_message), re.IGNORECASE)

    if match:
        return float(match.group(1))

    # Pattern for "Retry-After: X" header format
    pattern2 = r"Retry-After:\s*(\d+(?:\.\d+)?)"
    match2 = re.search(pattern2, str(error_message), re.IGNORECASE)

    if match2:
        return float(match2.group(1))

    return None


def with_retry(
    config: Optional[OpenAIRetryConfig] = None,
    retry_on: tuple = (RateLimitError, APIConnectionError, Timeout, APIError),
    websocket_handler: Optional[Any] = None,
    client_id: Optional[str] = None,
    task_id: Optional[str] = None
):
    """
    Decorator to add retry logic with exponential backoff to OpenAI API calls

    Args:
        config: OpenAIRetryConfig instance (uses default if None)
        retry_on: Tuple of exception types to retry on
        websocket_handler: Optional WebSocket handler for progress updates
        client_id: Optional client ID for WebSocket messages
        task_id: Optional task ID for tracking

    Example:
        @with_retry()
        def call_openai():
            return openai.ChatCompletion.create(...)
    """
    if config is None:
        config = OpenAIRetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Extract WebSocket parameters from kwargs if present
            ws_handler = kwargs.pop('websocket_handler', websocket_handler)
            ws_client_id = kwargs.pop('client_id', client_id)
            ws_task_id = kwargs.pop('task_id', task_id)

            delay = config.initial_delay
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    # Attempt the API call
                    result = func(*args, **kwargs)

                    # Log successful retry if not first attempt
                    if attempt > 0:
                        logger.info(
                            f"✅ OpenAI call succeeded on attempt {attempt + 1}/{config.max_retries + 1} "
                            f"for function '{func.__name__}'"
                        )

                        # Send success WebSocket update if handler available
                        if ws_handler and ws_client_id:
                            ws_handler.emit_progress(
                                ws_client_id,
                                ws_task_id or func.__name__,
                                'openai_retry',
                                f'API call succeeded after {attempt + 1} attempts',
                                100
                            )

                    return result

                except retry_on as e:
                    last_exception = e
                    error_msg = str(e)

                    # Don't retry if this was the last attempt
                    if attempt >= config.max_retries:
                        logger.error(
                            f"❌ OpenAI call failed after {config.max_retries + 1} attempts "
                            f"for function '{func.__name__}': {error_msg}"
                        )

                        # Send failure WebSocket update
                        if ws_handler and ws_client_id:
                            ws_handler.emit_error(
                                ws_client_id,
                                f"OpenAI API call failed after {config.max_retries + 1} attempts: {error_msg}"
                            )
                        break

                    # Extract wait time from error message if it's a rate limit error
                    actual_delay = delay
                    if isinstance(e, RateLimitError) or '429' in error_msg or 'rate' in error_msg.lower():
                        retry_after = extract_retry_after(error_msg)
                        if retry_after:
                            actual_delay = retry_after
                            logger.info(f"📊 Extracted retry-after time: {retry_after} seconds from error message")
                        else:
                            # Use exponential backoff if we can't extract the wait time
                            if config.jitter:
                                import random
                                jitter_factor = random.uniform(0.5, 1.5)
                                actual_delay = min(delay * jitter_factor, config.max_delay)
                            else:
                                actual_delay = min(delay, config.max_delay)
                    else:
                        # Use normal exponential backoff for non-rate-limit errors
                        if config.jitter:
                            import random
                            jitter_factor = random.uniform(0.5, 1.5)
                            actual_delay = min(delay * jitter_factor, config.max_delay)
                        else:
                            actual_delay = min(delay, config.max_delay)

                    # Log retry attempt
                    logger.warning(
                        f"⚠️  OpenAI call failed (attempt {attempt + 1}/{config.max_retries + 1}) "
                        f"for function '{func.__name__}': {error_msg}. "
                        f"Retrying in {actual_delay:.2f}s..."
                    )

                    # Send WebSocket progress updates during wait
                    if ws_handler and ws_client_id and actual_delay > 5:
                        # Send initial waiting message
                        ws_handler.emit_progress(
                            ws_client_id,
                            ws_task_id or func.__name__,
                            'openai_retry',
                            f'Rate limited. Waiting {actual_delay:.0f} seconds before retry (attempt {attempt + 1}/{config.max_retries + 1})',
                            0,
                            {'retry_after': actual_delay, 'attempt': attempt + 1}
                        )

                        # Update progress during wait for long delays
                        wait_intervals = 10  # Update every 10% of wait time
                        interval_duration = actual_delay / wait_intervals

                        for i in range(wait_intervals):
                            time.sleep(interval_duration)
                            progress = int((i + 1) * 100 / wait_intervals)
                            remaining = actual_delay - ((i + 1) * interval_duration)

                            ws_handler.emit_progress(
                                ws_client_id,
                                ws_task_id or func.__name__,
                                'openai_retry',
                                f'Waiting... {remaining:.0f} seconds remaining',
                                progress,
                                {'remaining': remaining, 'attempt': attempt + 1}
                            )
                    else:
                        # Just wait without progress updates for short delays
                        time.sleep(actual_delay)

                    # Increase delay for next retry (only if we didn't extract a specific wait time)
                    if not (isinstance(e, RateLimitError) or '429' in error_msg):
                        delay *= config.exponential_base

                except Exception as e:
                    # Don't retry on unexpected errors
                    logger.error(
                        f"❌ Unexpected error in OpenAI call for function '{func.__name__}': {str(e)}"
                    )

                    if ws_handler and ws_client_id:
                        ws_handler.emit_error(
                            ws_client_id,
                            f"Unexpected error in OpenAI API call: {str(e)}"
                        )
                    raise

            # If we got here, all retries failed
            raise last_exception

        return wrapper
    return decorator


def create_retry_wrapper(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0
):
    """
    Create a retry wrapper with custom configuration

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Configured retry decorator

    Example:
        retry = create_retry_wrapper(max_retries=3)

        @retry
        def my_openai_call():
            return openai.ChatCompletion.create(...)
    """
    config = OpenAIRetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay
    )
    return with_retry(config=config)


# Admin-configurable retry decorators that read from YAML config
def get_admin_configurable_retry():
    """
    Get retry decorator with admin-configurable settings from YAML.
    This allows administrators to adjust retry behavior via the UI.
    """
    try:
        from app.utils.app_config import ADMIN_MAX_RETRIES, ADMIN_RETRY_DELAY
        return with_retry(
            OpenAIRetryConfig(
                max_retries=ADMIN_MAX_RETRIES,  # Configurable via UI
                initial_delay=float(ADMIN_RETRY_DELAY),  # Configurable via UI
                max_delay=300.0,  # Allow up to 5 minutes wait for rate limits
                jitter=False  # Disable jitter when we extract exact wait times
            )
        )
    except ImportError:
        # Fallback if app_config not available
        return with_retry(
            OpenAIRetryConfig(
                max_retries=3,  # Default fallback
                initial_delay=2.0,
                max_delay=300.0,
                jitter=False
            )
        )


# Default retry decorator - now uses admin-configurable settings
retry_openai = get_admin_configurable_retry()


# Aggressive retry for critical operations
retry_openai_aggressive = with_retry(
    OpenAIRetryConfig(
        max_retries=5,  # More retries for critical operations
        initial_delay=2.0,
        max_delay=300.0,  # Allow long waits for rate limits
        jitter=False
    )
)


# Quick retry for real-time operations
retry_openai_quick = with_retry(
    OpenAIRetryConfig(
        max_retries=1,
        initial_delay=0.5,
        max_delay=5.0
    )
)


# WebSocket-aware retry decorator factory
def create_websocket_retry(
    websocket_handler=None,
    client_id=None,
    task_id=None,
    max_retries=None,  # Now defaults to admin config
    max_delay=300.0
):
    """
    Create a retry decorator with WebSocket progress updates

    Args:
        websocket_handler: WebSocket handler instance
        client_id: Client session ID
        task_id: Task identifier
        max_retries: Maximum retry attempts (uses admin config if None)
        max_delay: Maximum delay in seconds

    Returns:
        Configured retry decorator with WebSocket support
    """
    # Use admin-configurable retry count if not specified
    if max_retries is None:
        try:
            from app.utils.app_config import ADMIN_MAX_RETRIES
            max_retries = ADMIN_MAX_RETRIES
        except ImportError:
            max_retries = 3  # Fallback
    
    config = OpenAIRetryConfig(
        max_retries=max_retries,
        initial_delay=1.0,
        max_delay=max_delay,
        jitter=False
    )
    return with_retry(
        config=config,
        websocket_handler=websocket_handler,
        client_id=client_id,
        task_id=task_id
    )
