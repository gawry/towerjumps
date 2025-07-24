"""
Tower Jumps Analysis Package - Mobile carrier data analysis for tower jump detection.
"""

import logging
import os
import sys
from typing import Any

import structlog

__version__ = "0.0.1"


def configure_logging(level: str = "ERROR", enable_dev_logging: bool = False) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_dev_logging: Enable development-friendly logging with colors and pretty printing
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if enable_dev_logging or os.getenv("TOWERJUMPS_DEV_LOGGING", "").lower() == "true":
        # Development-friendly logging with colors and pretty printing
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # Production logging with JSON output
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Get a configured structlog logger."""
    return structlog.get_logger(name)
