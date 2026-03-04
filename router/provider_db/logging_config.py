"""
Logging configuration for provider.db builder.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_size_mb: int = 10,
    backup_count: int = 5,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up structured logging for provider.db builder.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        max_size_mb: Maximum log file size in MB
        backup_count: Number of backup files to keep
        format_string: Custom log format string
        
    Returns:
        Root logger configured with handlers
    """
    # Default format
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(filename)s:%(lineno)d] - %(message)s"
        )
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log_file specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with consistent configuration.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class StructuredLogger:
    """
    Structured logger for provider.db operations.
    Provides consistent log messages for common operations.
    """
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
    
    # Standard logging methods
    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)
    
    def build_started(self, db_path: str, force: bool = False) -> None:
        """Log build start."""
        self.logger.info(
            "Build started",
            extra={
                "operation": "build_start",
                "db_path": db_path,
                "force_rebuild": force
            }
        )
    
    def build_completed(self, duration: float, stats: dict) -> None:
        """Log build completion."""
        self.logger.info(
            "Build completed",
            extra={
                "operation": "build_complete",
                "duration_seconds": duration,
                "models_total": stats.get("total_models", 0),
                "sources_succeeded": len(stats.get("sources_succeeded", [])),
                "sources_failed": len(stats.get("sources_failed", []))
            }
        )
    
    def source_fetch_started(self, source_name: str) -> None:
        """Log source fetch start."""
        self.logger.debug(
            f"Fetching source: {source_name}",
            extra={"operation": "source_fetch_start", "source": source_name}
        )
    
    def source_fetch_completed(self, source_name: str, model_count: int) -> None:
        """Log source fetch completion."""
        self.logger.info(
            f"Source fetched: {source_name} ({model_count} models)",
            extra={
                "operation": "source_fetch_complete",
                "source": source_name,
                "model_count": model_count
            }
        )
    
    def source_fetch_failed(self, source_name: str, error: str) -> None:
        """Log source fetch failure."""
        self.logger.error(
            f"Source fetch failed: {source_name} - {error}",
            extra={
                "operation": "source_fetch_failed",
                "source": source_name,
                "error": error
            }
        )
    
    def critical_source_failed(self, source_name: str) -> None:
        """Log critical source failure."""
        self.logger.warning(
            f"Critical source failed: {source_name}",
            extra={
                "operation": "critical_source_failed",
                "source": source_name,
                "severity": "warning"
            }
        )
    
    def database_write_started(self, model_count: int) -> None:
        """Log database write start."""
        self.logger.info(
            f"Writing {model_count} models to database",
            extra={
                "operation": "db_write_start",
                "model_count": model_count
            }
        )
    
    def database_write_completed(self, inserted: int, updated: int) -> None:
        """Log database write completion."""
        self.logger.info(
            f"Database write completed: {inserted} inserted, {updated} updated",
            extra={
                "operation": "db_write_complete",
                "inserted_count": inserted,
                "updated_count": updated
            }
        )
    
    def alias_generation_completed(self, alias_count: int) -> None:
        """Log alias generation completion."""
        self.logger.info(
            f"Alias generation completed: {alias_count} aliases created",
            extra={
                "operation": "alias_generation_complete",
                "alias_count": alias_count
            }
        )
    
    def validation_passed(self, checks: list) -> None:
        """Log validation success."""
        self.logger.info(
            f"Validation passed: {len(checks)} checks",
            extra={
                "operation": "validation_passed",
                "check_count": len(checks),
                "checks": checks
            }
        )
    
    def validation_failed(self, checks: list, errors: list) -> None:
        """Log validation failure."""
        self.logger.error(
            f"Validation failed: {len(errors)} errors",
            extra={
                "operation": "validation_failed",
                "check_count": len(checks),
                "error_count": len(errors),
                "errors": errors
            }
        )
    
    def rate_limit_applied(self, source: str, delay: float) -> None:
        """Log rate limiting."""
        self.logger.debug(
            f"Rate limiting applied to {source}: {delay:.2f}s delay",
            extra={
                "operation": "rate_limit",
                "source": source,
                "delay_seconds": delay
            }
        )
    
    def sql_injection_prevented(self, model_id: str, sanitized_id: str) -> None:
        """Log SQL injection prevention."""
        self.logger.warning(
            f"SQL injection prevented: sanitized '{model_id}' to '{sanitized_id}'",
            extra={
                "operation": "sql_injection_prevention",
                "original_id": model_id,
                "sanitized_id": sanitized_id,
                "severity": "warning"
            }
        )
    
    def score_validation_failed(self, score_name: str, score: float, min_val: float, max_val: float) -> None:
        """Log score validation failure."""
        self.logger.error(
            f"Score validation failed: {score_name}={score} not in range [{min_val}, {max_val}]",
            extra={
                "operation": "score_validation_failed",
                "score_name": score_name,
                "score_value": score,
                "min_value": min_val,
                "max_value": max_val
            }
        )


# Default logger instance for backward compatibility
logger = get_logger(__name__)