"""
Structured logging configuration for UdyamSetu AI.
Formats log records with ISO timestamps, module context, and request IDs.
"""

import logging
import sys
from typing import Any, Dict


class StructuredLogFormatter(logging.Formatter):
    """Console/JSON log formatter with contextual metadata."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", "-")
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        log_line = (
            f"[{timestamp}] [{record.levelname:<7}] "
            f"[{record.name}] [req:{request_id}] {record.getMessage()}"
        )
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)
        return log_line


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root and application loggers."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers if reconfigured
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    # Silence verbose 3rd party logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
