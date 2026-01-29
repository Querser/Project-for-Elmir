import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    # Фолбэк, чтобы даже при косяке env не падало
    DATABASE_URL = "postgresql+psycopg2://postgres:postgres@db:5432/volleyball_db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
