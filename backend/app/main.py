from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1 import api_router as api_v1_router
from app.core.config import get_settings
from app.core.exceptions import setup_exception_handlers
from app.core.logger import configure_logging
from app.core.middleware import RequestLoggingMiddleware, TelegramAuthMiddleware

from app.db.session import engine  # sync engine

settings = get_settings()
configure_logging()

logger = logging.getLogger("app.main")


def _truthy_env(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip().strip('"').strip("'").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def _should_run_migrations() -> bool:
    # можно выключить в проде: RUN_MIGRATIONS_ON_STARTUP=0
    return _truthy_env("RUN_MIGRATIONS_ON_STARTUP", default=True)


def _find_alembic_ini() -> Optional[Path]:
    base = Path(__file__).resolve().parents[1]  # .../app
    candidates = [
        base / "alembic.ini",
        base.parent / "alembic.ini",
        (base / ".." / "alembic.ini").resolve(),
    ]
    for p in candidates:
        p = p.resolve()
        if p.exists():
            return p
    return None


def _wait_for_db(max_attempts: int = 30, delay_sec: float = 0.5) -> None:
    last_exc: Exception | None = None
    for _ in range(max_attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:
            last_exc = exc
            time.sleep(delay_sec)
    raise RuntimeError("Database is not reachable") from last_exc


def _run_migrations() -> None:
    """
    1) ждём БД
    2) берём advisory lock (чтобы при reload/нескольких процессах миграции не дрались)
    3) alembic upgrade head
    """
    if not _should_run_migrations():
        logger.info("DB bootstrap: skipped (RUN_MIGRATIONS_ON_STARTUP=0)")
        return

    _wait_for_db()

    alembic_ini = _find_alembic_ini()
    if not alembic_ini:
        raise RuntimeError(
            "alembic.ini not found. Ensure it exists in project root and is mounted into container."
        )

    try:
        from alembic import command  # type: ignore
        from alembic.config import Config  # type: ignore
    except Exception as exc:
        raise RuntimeError("Alembic is not available. Add 'alembic' to backend requirements.") from exc

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)

    lock_key = 910_004_221_337  # любое фиксированное bigint
    logger.info("DB bootstrap: acquiring advisory lock %s", lock_key)

    with engine.connect() as conn:
        # advisory lock держится до закрытия соединения
        conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": lock_key})
        try:
            logger.info("DB bootstrap: alembic upgrade head (ini=%s)", str(alembic_ini))
            command.upgrade(cfg, "head")
            logger.info("DB bootstrap: migrations applied")
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": lock_key})
            logger.info("DB bootstrap: advisory lock released %s", lock_key)


app = FastAPI(
    title="Volleyball MiniApp API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

media_root = Path(__file__).resolve().parents[1] / "media"
media_root.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_root)), name="media")


@app.on_event("startup")
def _startup() -> None:
    _run_migrations()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TelegramAuthMiddleware)
app.add_middleware(RequestLoggingMiddleware)

setup_exception_handlers(app)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def healthcheck():
    return {"status": "ok"}
