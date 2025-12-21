# backend/app/core/deps.py
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.core.middleware import get_current_user  # просто реэкспорт


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async-зависимость для работы с БД.

    Используется там, где сервисы ожидают AsyncSession
    (долги, баны, автобан и т.п.).
    """
    async with async_session_maker() as session:
        # session закроется автоматически после выхода из контекста
        yield session
