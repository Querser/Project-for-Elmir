from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# В Docker backend по умолчанию ходит к контейнеру PostgreSQL по имени volleyball_db.
# Если settings.database_url задан, он имеет приоритет.
SQLALCHEMY_DATABASE_URL = (
    settings.database_url
    or "postgresql+psycopg://postgres:postgres@volleyball_db:5432/volleyball_db"
)

# -------- СИНХРОННЫЙ движок (старый код, тренировки, профиль и т.п.) --------

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Синхронная сессия БД — используется существующими зависимостями.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------- АСИНХРОННЫЙ движок и sessionmaker (новый код: баны, долги и т.п.) --------

def _make_async_url(url: str) -> str:
    """
    Преобразуем sync-URL в async-URL для SQLAlchemy.

    - Если драйвер уже async (содержит 'async') — возвращаем как есть.
    - Если это psycopg3 (postgresql+psycopg) — переводим в postgresql+psycopg_async.
    """
    sa_url = make_url(url)
    driver = sa_url.drivername or ""

    # Уже async-диалект — ничего не меняем
    if "async" in driver:
        return url

    # psycopg3 sync -> psycopg3 async
    if driver in {"postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
        sa_url = sa_url.set(drivername="postgresql+psycopg_async")
        return sa_url.render_as_string(hide_password=False)

    # На всякий случай — без изменений
    return url


ASYNC_SQLALCHEMY_DATABASE_URL = _make_async_url(SQLALCHEMY_DATABASE_URL)

# Асинхронный движок (используется в app/core/deps.py через async_session_maker)
async_engine: AsyncEngine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)
