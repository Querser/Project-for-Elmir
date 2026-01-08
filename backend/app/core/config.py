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


class Settings(BaseModel):
    project_name: str = os.getenv("PROJECT_NAME", "Volleyball Training API")
    api_v1_str: str = os.getenv("API_V1_STR", "/api/v1")
    environment: str = "development"


    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_webapp_url: str = os.getenv("TELEGRAM_WEBAPP_URL", "")
    telegram_admin_chat_id: int = int(os.getenv("TELEGRAM_ADMIN_CHAT_ID", "0") or 0)
    telegram_admin_user_id: int = int(os.getenv("TELEGRAM_ADMIN_USER_ID", "0") or 0)

    # 🔥 главное: нормальное значение по умолчанию, чтобы контейнер не падал,
    # даже если DATABASE_URL не задан
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@db:5432/volleyball_db",
    )

    # ✅ алиас — чтобы старый код settings.DATABASE_URL НЕ ЛОМАЛСЯ
    @property
    def DATABASE_URL(self) -> str:
        return self.database_url


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
