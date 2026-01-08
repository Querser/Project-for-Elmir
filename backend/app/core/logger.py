# app/core/logger.py
from __future__ import annotations

import logging
import os
import sys

try:
    # обычно settings тут
    from app.core.config import settings  # type: ignore
except Exception:
    settings = None  # type: ignore


def _detect_environment() -> str:
    """
    Возвращаем environment максимально безопасно:
    - сначала пробуем settings.environment
    - потом ENVIRONMENT из окружения
    - иначе development
    """
    if settings is not None:
        env = getattr(settings, "environment", None)
        if env:
            return str(env)

    return os.getenv("ENVIRONMENT", "development")


def configure_logging() -> None:
    env = _detect_environment().strip().lower()

    level = logging.DEBUG if env in {"dev", "development", "local"} else logging.INFO

    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # чуть нормализуем шумные логгеры
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
