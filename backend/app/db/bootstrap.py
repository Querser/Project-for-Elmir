"""
DB bootstrap on application startup.

- Waits for Postgres to be reachable
- Runs Alembic migrations (upgrade head)
- Fallback: Base.metadata.create_all() if Alembic isn't available or config missing

This removes runtime errors like:
  psycopg2.errors.UndefinedTable: relation "users"/"levels" does not exist
"""

from __future__ import annotations

import importlib
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

logger = logging.getLogger(__name__)


def _wait_for_db(max_attempts: int = 30, delay_sec: float = 0.5) -> None:
    last_exc: Exception | None = None
    for _ in range(max_attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(delay_sec)
    raise RuntimeError(f"Database is not reachable after {max_attempts} attempts") from last_exc


def _find_project_root() -> Path:
    # /app/app/db/bootstrap.py -> parents[2] == /app
    return Path(__file__).resolve().parents[2]


def _find_alembic_ini(project_root: Path) -> Optional[Path]:
    candidates = [
        project_root / "alembic.ini",
        project_root / "backend" / "alembic.ini",
        project_root / "app" / "alembic.ini",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _run_alembic_migrations() -> bool:
    try:
        from alembic import command  # type: ignore
        from alembic.config import Config  # type: ignore
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alembic is not available (%s). Will fallback to create_all().", exc)
        return False

    project_root = _find_project_root()
    alembic_ini = _find_alembic_ini(project_root)
    if not alembic_ini:
        logger.warning("alembic.ini not found. Will fallback to create_all().")
        return False

    cfg = Config(str(alembic_ini))

    # Важно: подставляем реальный URL (из env / settings)
    cfg.set_main_option("sqlalchemy.url", settings.database_url)

    # На всякий случай: если script_location не задан в ini
    try:
        script_location = cfg.get_main_option("script_location")
    except Exception:  # noqa: BLE001
        script_location = None

    default_alembic_dir = project_root / "alembic"
    if (not script_location) and default_alembic_dir.exists():
        cfg.set_main_option("script_location", str(default_alembic_dir))

    logger.info("Running Alembic migrations: upgrade head")
    command.upgrade(cfg, "head")
    logger.info("Alembic migrations applied successfully")
    return True


def _import_all_models() -> None:
    """
    Чтобы Base увидела все модели (если проект устроен так, что
    модели регистрируются импортом модулей).
    """
    try:
        import pkgutil
        import app.models as models_pkg  # noqa: WPS433
    except Exception:
        return

    for mod in pkgutil.iter_modules(models_pkg.__path__):
        importlib.import_module(f"{models_pkg.__name__}.{mod.name}")


def _get_base() -> object:
    """
    Пытаемся найти Base в типичных местах.
    Подстрой под свой проект, если Base лежит иначе.
    """
    for mod_name in ("app.db.base", "app.db.base_class", "app.models.base"):
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "Base"):
                return getattr(mod, "Base")
        except Exception:
            continue
    raise RuntimeError("Could not import SQLAlchemy Base (tried app.db.base, app.db.base_class, app.models.base)")


def _create_all_fallback() -> None:
    _import_all_models()
    Base = _get_base()
    # Base должен иметь metadata
    if not hasattr(Base, "metadata"):
        raise RuntimeError("Imported Base has no metadata attribute")
    Base.metadata.create_all(bind=engine)
    logger.info("Fallback schema create_all() done")


def init_database() -> None:
    """
    Call this on FastAPI startup before serving requests.
    """
    _wait_for_db()
    ok = _run_alembic_migrations()
    if not ok:
        _create_all_fallback()