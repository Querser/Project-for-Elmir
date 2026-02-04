"""
SQLAlchemy engine/session.

Этап 2: единый стиль БД — SYNC (Session + create_engine)
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DEFAULT_DATABASE_URL, settings


def _fallback_db_url() -> str:
    """
    Фоллбек, если DATABASE_URL пустой/битый.
    Собираем из POSTGRES_* (они у тебя прокидываются в docker-compose),
    а если и их нет — используем DEFAULT_DATABASE_URL.
    """
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "volleyball_db")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return url.strip() or DEFAULT_DATABASE_URL


_db_url = (getattr(settings, "database_url", "") or "").strip()
if not _db_url:
    _db_url = _fallback_db_url()

engine = create_engine(
    _db_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()