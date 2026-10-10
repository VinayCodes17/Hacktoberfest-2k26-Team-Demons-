"""Allowlisted JSON events: never format request bodies, query strings or errors."""
import json
import logging


class SafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = record.getMessage()
        if event not in {"request_completed", "request_failed"}:
            event = "application_event"
        payload = {"level": record.levelname, "event": event}
        for key in ("request_id", "status", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("hisabhparakh")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(SafeFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
