"""
Provider DB Utilities Module

Provides common utilities for:
- Rate limiting
- Retry logic with backoff
- Input sanitization
- Metrics collection
"""

import time
import hashlib
import logging
import asyncio
from typing import Callable, Any, Optional
from functools import wraps
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 1.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
    
    async def wait(self):
        """Wait if necessary to maintain rate limit."""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply rate limiting to a function."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await self.wait()
            return await func(*args, **kwargs)
        return wrapper


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0
):
    """
    Decorator that retries a function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay in seconds
        exponential_base: Multiplier for delay on each retry
        max_delay: Maximum delay between retries
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def sanitize_model_id(model_id: str) -> str:
    """
    Sanitize model ID to prevent injection attacks.
    
    Args:
        model_id: Raw model ID string
        
    Returns:
        Sanitized model ID
    """
    if not model_id:
        raise ValueError("Model ID cannot be empty")
    
    # Remove any null bytes or control characters
    sanitized = "".join(
        char for char in model_id 
        if char.isprintable() or char in ["/", "-", "_", ".", ":"]
    )
    
    # Limit length
    max_length = 200
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    # Basic validation - must match pattern provider/model-name
    if "/" not in sanitized:
        raise ValueError(f"Invalid model ID format: {model_id}")
    
    return sanitized


def validate_score_range(score: float, score_name: str, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """
    Validate that a score is within the expected range.
    
    Args:
        score: The score value
        score_name: Name of the score for error messages
        min_val: Minimum valid value
        max_val: Maximum valid value
        
    Returns:
        Validated score
        
    Raises:
        ValueError: If score is out of range
    """
    if not isinstance(score, (int, float)):
        raise ValueError(f"{score_name} must be a number, got {type(score)}")
    
    if score < min_val or score > max_val:
        raise ValueError(f"{score_name} must be between {min_val} and {max_val}, got {score}")
    
    return float(score)


def validate_elo_rating(elo: int) -> int:
    """
    Validate ELO rating is within valid range.
    
    Args:
        elo: Raw ELO rating
        
    Returns:
        Validated ELO rating
        
    Raises:
        ValueError: If ELO is invalid
    """
    if not isinstance(elo, int):
        raise ValueError(f"ELO must be an integer, got {type(elo)}")
    
    if elo < 0:
        raise ValueError(f"ELO cannot be negative, got {elo}")
    
    # Cap at reasonable maximum
    if elo > 2000:
        logger.warning(f"ELO rating {elo} seems unusually high, capping at 2000")
        elo = 2000
    
    return elo


class MetricsCollector:
    """Collects metrics for monitoring scraper performance."""
    
    def __init__(self):
        self.metrics: dict[str, Any] = {
            "sources_attempted": [],
            "sources_succeeded": [],
            "sources_failed": [],
            "models_processed": 0,
            "models_with_scores": 0,
            "errors": [],
            "start_time": None,
            "end_time": None,
        }
    
    def start(self):
        """Mark the start of a metrics collection period."""
        self.metrics["start_time"] = datetime.now(timezone.utc)
    
    def end(self):
        """Mark the end of a metrics collection period."""
        self.metrics["end_time"] = datetime.now(timezone.utc)
    
    def record_source_attempted(self, source: str):
        """Record that a source was attempted."""
        if source not in self.metrics["sources_attempted"]:
            self.metrics["sources_attempted"].append(source)
    
    def record_source_succeeded(self, source: str):
        """Record that a source succeeded."""
        if source not in self.metrics["sources_succeeded"]:
            self.metrics["sources_succeeded"].append(source)
    
    def record_source_failed(self, source: str):
        """Record that a source failed."""
        if source not in self.metrics["sources_failed"]:
            self.metrics["sources_failed"].append(source)
    
    def record_error(self, error: str):
        """Record an error message."""
        self.metrics["errors"].append({
            "message": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    def increment_models_processed(self):
        """Increment the models processed counter."""
        self.metrics["models_processed"] += 1
    
    def increment_models_with_scores(self):
        """Increment the models with scores counter."""
        self.metrics["models_with_scores"] += 1
    
    def get_summary(self) -> dict[str, Any]:
        """Get a summary of collected metrics."""
        duration = None
        if self.metrics["start_time"] and self.metrics["end_time"]:
            duration = (self.metrics["end_time"] - self.metrics["start_time"]).total_seconds()
        
        return {
            "duration_seconds": duration,
            "sources_attempted": len(self.metrics["sources_attempted"]),
            "sources_succeeded": len(self.metrics["sources_succeeded"]),
            "sources_failed": len(self.metrics["sources_failed"]),
            "models_processed": self.metrics["models_processed"],
            "models_with_scores": self.metrics["models_with_scores"],
            "error_count": len(self.metrics["errors"]),
        }
    
    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        summary = self.get_summary()
        
        for key, value in summary.items():
            if value is not None:
                metric_name = key.replace("-", "_")
                lines.append(f"provider_db_{metric_name} {value}")
        
        return "\n".join(lines)


def compute_sha256(filepath: str) -> str:
    """
    Compute SHA256 checksum of a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Hex-encoded SHA256 checksum
    """
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
