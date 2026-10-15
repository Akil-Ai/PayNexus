"""Structured JSON logging with correlation IDs. No PII in logs."""
import json
import logging
import traceback
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Any, Dict, Optional

correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class JSONFormatter(getattr(logging, "Formatter", object)):  # type: ignore[misc]
    """Format log records as structured JSON. Never logs PII fields."""

    SENSITIVE_KEYS = frozenset({
        "password", "secret", "token", "pan", "card_number",
        "account_number", "cvv", "pin", "ssn", "nid", "passport",
        "authorization", "x-api-key", "field_encryption_key",
    })

    def format(self, record: Any) -> str:  # noqa: A003
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


def get_logger(name: str) -> Any:
    return getattr(logging, "getLogger", lambda n: None)(name)


def setup_logging():
    get_logger_fn = getattr(logging, "getLogger", None)
    if get_logger_fn:
        root = get_logger_fn()
        root.setLevel(getattr(logging, "INFO", 20))
        if not any(isinstance(h.formatter, JSONFormatter) for h in root.handlers):
            stream_handler_cls = getattr(logging, "StreamHandler", None)
            if stream_handler_cls:
                handler = stream_handler_cls()
                handler.setFormatter(JSONFormatter())
                root.addHandler(handler)

