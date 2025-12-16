# backend/app/db/session.py
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# В Docker backend должен ходить к контейнеру PostgreSQL по имени сервиса: volleyball_db.
SQLALCHEMY_DATABASE_URL = (
    settings.database_url
    or "postgresql+psycopg://postgres:postgres@volleyball_db:5432/volleyball_db"
)

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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
