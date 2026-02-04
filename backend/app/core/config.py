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


_backend_root = Path(__file__).resolve().parent.parent.parent
_repo_root = _backend_root.parent

# Ищем .env.dev/.env сначала в backend/, затем в корне репозитория
for candidate in (
    _backend_root / ".env.dev",
    _repo_root / ".env.dev",
    _backend_root / ".env",
    _repo_root / ".env",
):
    if candidate.exists():
        load_dotenv(candidate)
        break
else:
    load_dotenv()


def _env_str(name: str, default: str = "") -> str:
    """
    Безопасно читает строковую переменную окружения:
    - если переменная НЕ задана -> default
    - если переменная задана, но пустая/пробелы -> default
    """
    val = os.getenv(name)
    if val is None:
        return default
    val = str(val).strip()
    return val if val else default


def _env_int(name: str, default: int = 0) -> int:
    val = _env_str(name, str(default))
    try:
        return int(val)
    except ValueError:
        return default


DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@db:5432/volleyball_db"


class Settings(BaseModel):
    project_name: str = _env_str("PROJECT_NAME", "Volleyball Training API")
    api_v1_str: str = _env_str("API_V1_STR", "/api/v1")

    # ✅ теперь реально берём из окружения (и не ломаемся на пустом значении)
    environment: str = _env_str("ENVIRONMENT", "development")

    telegram_bot_token: str = _env_str("TELEGRAM_BOT_TOKEN", "")
    telegram_webapp_url: str = _env_str("TELEGRAM_WEBAPP_URL", "")
    telegram_admin_chat_id: int = _env_int("TELEGRAM_ADMIN_CHAT_ID", 0)
    telegram_admin_user_id: int = _env_int("TELEGRAM_ADMIN_USER_ID", 0)

    # 🔥 главное: если DATABASE_URL не задан ИЛИ задан как пустая строка -> берём дефолт
    database_url: str = _env_str("DATABASE_URL", DEFAULT_DATABASE_URL)

    # ✅ алиас — чтобы старый код settings.DATABASE_URL НЕ ЛОМАЛСЯ
    @property
    def DATABASE_URL(self) -> str:
        return self.database_url


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()