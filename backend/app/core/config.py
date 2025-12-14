# app/core/config.py
"""
Модуль конфигурации проекта.

Все настройки читаются из переменных окружения.
Для локальной разработки мы дополнительно подхватываем значения из .env.dev.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

# При запуске backend из репозитория пытаемся прочитать .env.dev из корня проекта.
# Если файла нет (например, внутри Docker-контейнера), просто игнорируем.
load_dotenv(".env.dev")


class Settings(BaseModel):
    environment: str = os.getenv("ENVIRONMENT", "development")

    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))

    database_url: str = os.getenv("DATABASE_URL", "")

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_webapp_url: str | None = os.getenv("TELEGRAM_WEBAPP_URL") or None


@lru_cache
def get_settings() -> Settings:
    """
    Возвращает singleton-объект с настройками.

    Используем lru_cache, чтобы не создавать объект каждый раз заново.
    """
    return Settings()
