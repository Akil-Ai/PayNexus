"""Structured JSON logging with correlation IDs. No PII in logs."""
import json
import logging
import traceback
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Any, Dict, Optional

correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """Format log records as structured JSON. Never logs PII fields."""

    SENSITIVE_KEYS = frozenset({
        "password", "secret", "token", "pan", "card_number",
        "account_number", "cvv", "pin", "ssn", "nid", "passport",
        "authorization", "x-api-key", "field_encryption_key",
    })

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        cid = correlation_id_var.get()
        uid = user_id_var.get()
        if cid:
            log_entry["correlation_id"] = cid
        if uid:
            log_entry["user_id"] = uid

        if record.exc_info:
            log_entry["exception"] = traceback.format_exception(*record.exc_info)

        # Merge extra fields but redact sensitive ones
        extra = {
            k: "***REDACTED***" if k.lower() in self.SENSITIVE_KEYS else v
            for k, v in record.__dict__.items()
            if k not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "message",
                "module", "msecs", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread", "threadName",
            )
        }
        if extra:
            log_entry["extra"] = extra

        return json.dumps(log_entry, default=str)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h.formatter, JSONFormatter) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        root.addHandler(handler)

