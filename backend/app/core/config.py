# backend/app/core/config.py
"""
Модуль конфигурации проекта.

Все настройки читаются из переменных окружения.
Для локальной разработки дополнительно подхватываем значения из .env.dev,
если такой файл найден в текущей или родительских директориях.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


def _load_local_env() -> None:
    """
    Ищем файл .env.dev, поднимаясь вверх от текущего файла.
    Работает и при запуске из репозитория, и внутри Docker-контейнера.
    """
    cfg_path = Path(__file__).resolve()
    for parent in (cfg_path.parent, *cfg_path.parents):
        candidate = parent / ".env.dev"
        if candidate.is_file():
            load_dotenv(candidate)
            break


# Подгружаем .env.dev, если он есть
_load_local_env()


class Settings(BaseModel):
    # Общее
    environment: str = os.getenv("ENVIRONMENT", "development")

    # HTTP server
    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))

    # БД
    database_url: str = os.getenv("DATABASE_URL", "")

    # Telegram
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_webapp_url: str | None = os.getenv("TELEGRAM_WEBAPP_URL") or None


@lru_cache
def get_settings() -> Settings:
    """
    Возвращает singleton-объект с настройками.
    """
    return Settings()


# Глобальный объект настроек, чтобы везде писать from app.core.config import settings
settings: Settings = get_settings()
