"""
Centralized structured JSONL logging for the trading bot.
All log records are written as newline-delimited JSON to a file
and optionally echoed to stderr via Rich.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_FILE = os.getenv("LOG_FILE", "logs/trading_bot.jsonl")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class JSONLHandler(logging.Handler):
    """Writes each log record as a single JSON line to a file."""

    def __init__(self, filepath: str) -> None:
        super().__init__()
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    # Attributes present on every LogRecord by default — anything else is extra
    _DEFAULT_ATTRS: set[str] = set(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
    ) | {"message", "asctime"}

    def emit(self, record: logging.LogRecord) -> None:
        log_entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exc"] = self.formatException(record.exc_info)
        # Capture any extra fields passed via logger.info("msg", extra={...})
        extra = {
            k: v for k, v in record.__dict__.items()
            if k not in self._DEFAULT_ATTRS and k != "taskName"
        }
        if extra:
            log_entry["extra"] = extra
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, default=str) + "\n")
        except Exception:
            pass  # never let logging crash the app


def get_logger(name: str = "trading_bot") -> logging.Logger:
    """Return a configured logger that writes JSONL to disk."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.addHandler(JSONLHandler(LOG_FILE))
    logger.propagate = False
    return logger


def tail_logs(n: int = 50, level_filter: str | None = None) -> list[dict[str, Any]]:
    """Read the last *n* log entries from the JSONL file, optionally filtered by level."""
    path = Path(LOG_FILE)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    records: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            if level_filter and rec.get("level", "").upper() != level_filter.upper():
                continue
            records.append(rec)
        except json.JSONDecodeError:
            continue
    return records[-n:]
