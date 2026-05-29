"""
DataGod Structured Logging Configuration
Provides JSON-formatted structured logging with request-id tracking
"""

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "action"):
            log_entry["action"] = record.action
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "path"):
            log_entry["path"] = record.path

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class RequestContextFilter(logging.Filter):
    """Filter that adds request context to log records."""

    def __init__(self):
        super().__init__()
        self._request_id: Optional[str] = None
        self._user_id: Optional[str] = None

    def set_context(self, request_id: str, user_id: Optional[str] = None):
        self._request_id = request_id
        self._user_id = user_id

    def clear_context(self):
        self._request_id = None
        self._user_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self._request_id or "no-request"
        record.user_id = self._user_id or "anonymous"
        return True


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


def setup_structured_logging(
    level: str = "INFO",
    json_format: bool = True,
) -> logging.Logger:
    """
    Configure structured logging for the DataGod application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (True) or human-readable (False)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("datagod")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    if json_format:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s"
            )
        )

    # Add request context filter
    context_filter = RequestContextFilter()
    handler.addFilter(context_filter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger


# Singleton logger instance
_logger: Optional[logging.Logger] = None
_context_filter: Optional[RequestContextFilter] = None


def get_logger() -> logging.Logger:
    """Get the singleton structured logger."""
    global _logger
    if _logger is None:
        _logger = setup_structured_logging()
    return _logger


def get_context_filter() -> RequestContextFilter:
    """Get the request context filter."""
    global _context_filter
    if _context_filter is None:
        _context_filter = RequestContextFilter()
    return _context_filter
