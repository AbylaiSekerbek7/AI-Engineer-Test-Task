from __future__ import annotations

import contextvars
import logging
import sys
from typing import Optional

REQUEST_ID_CTX: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Injects request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID_CTX.get()
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging with request_id support."""
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.addFilter(RequestIdFilter())

    fmt = "%(asctime)s | %(levelname)s | request_id=%(request_id)s | %(name)s | %(message)s"
    handler.setFormatter(logging.Formatter(fmt))

    # Avoid duplicate handlers on reload
    root.handlers = [handler]


def set_request_id(request_id: Optional[str]) -> str:
    """Set request_id into context and return the value used."""
    rid = request_id or "-"
    REQUEST_ID_CTX.set(rid)
    return rid

def get_request_id() -> str:
    return REQUEST_ID_CTX.get()
