# app/core/logger.py

from __future__ import annotations

import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    """
    Простая настройка логирования для проекта.
    """
    settings = get_settings()
    level = logging.DEBUG if settings.environment == "development" else logging.INFO

    root_logger = logging.getLogger("app")
    root_logger.setLevel(level)

    # Если уже настроен (hot-reload и т.п.) — не плодим хендлеры
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # уменьшим шум от SQLAlchemy
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
