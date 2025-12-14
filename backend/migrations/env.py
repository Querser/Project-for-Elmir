from logging.config import fileConfig
import os
import sys

from sqlalchemy import create_engine, pool
from alembic import context

# === Настройка путей, чтобы 'app' был виден ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # путь к backend
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
# ===============================================

config = context.config

# Логирование (из alembic.ini)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Импортируем модели
from app.models import Base

target_metadata = Base.metadata

# ВАЖНО: для миграций в dev мы ЖЁСТКО задаём URL к Postgres в контейнере db
DB_URL = "postgresql+psycopg://postgres:postgres@db:5432/volleyball_db"


def run_migrations_offline() -> None:
    """Запуск миграций в 'offline' режиме."""
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в 'online' режиме."""
    connectable = create_engine(
        DB_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
