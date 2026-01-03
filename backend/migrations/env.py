from __future__ import annotations

from logging.config import fileConfig
import os
import sys

from alembic import context
from sqlalchemy import create_engine, pool

# === Настройка путей, чтобы 'app' был виден ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # путь к backend
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
# ===============================================

config = context.config

# Логирование (из alembic.ini)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ВАЖНО: сначала импортируем пакет models, чтобы он подтянул ВСЕ модули моделей
import app.models  # noqa: F401
from app.models import Base

target_metadata = Base.metadata

# URL: можно переопределять переменной окружения, но dev-дефолт оставляем
DB_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("SQLALCHEMY_DATABASE_URI")
    or config.get_main_option("sqlalchemy.url")
    or "postgresql+psycopg://postgres:postgres@db:5432/volleyball_db"
)


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DB_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
