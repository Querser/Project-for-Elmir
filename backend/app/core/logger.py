# app/core/logger.py
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

try:
    from app.core.config import settings  # type: ignore
except Exception:
    settings = None  # type: ignore


def _detect_environment() -> str:
    if settings is not None:
        env = getattr(settings, "environment", None)
        if env:
            return str(env)
    return os.getenv("ENVIRONMENT", "development")


def configure_logging() -> None:
    env = _detect_environment().strip().lower()
    level = logging.DEBUG if env in {"dev", "development", "local"} else logging.INFO
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(stream_handler)

    app_log_file = ""
    if settings is not None:
        app_log_file = str(getattr(settings, "app_log_file", "") or "").strip()
    if not app_log_file:
        app_log_file = str(Path(__file__).resolve().parents[2] / "logs" / "app.log")

    try:
        log_path = Path(app_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(file_handler)
    except Exception:
        root.exception("Failed to configure file logging")

    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)

