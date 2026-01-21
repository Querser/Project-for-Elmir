# app/core/middleware.py
from __future__ import annotations

import logging
import os
import time
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

log = logging.getLogger("app.middleware")


def _env_truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def _is_dev_env() -> bool:
    env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    return env in {"dev", "development", "local"}


def _dev_mode_enabled() -> bool:
    # Явный dev-тумблер
    if _env_truthy("ALLOW_INSECURE_HEADER_AUTH", False):
        return True
    # Твой dev-флаг
    if _env_truthy("DEV_AUTO_CREATE_USER_FROM_HEADER", False):
        return True
    # Если задан дефолтный TG — это тоже dev-настройка
    if (os.getenv("DEV_DEFAULT_TELEGRAM_ID") or "").strip():
        return True
    # По окружению
    if _is_dev_env():
        return True
    return False


def _unauthorized(required_header: str = "X-Telegram-Init-Data") -> JSONResponse:
    return JSONResponse(
        {
            "error": {
                "code": "unauthorized",
                "message": "Пользователь не авторизован через Telegram",
                "details": {"required_header": required_header},
            }
        },
        status_code=401,
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Только логирование запросов (не авторизация).
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        start = time.perf_counter()
        response: Optional[Response] = None
        try:
            response = await call_next(request)
            return response
        finally:
            took_ms = (time.perf_counter() - start) * 1000.0
            status_code = getattr(response, "status_code", 500)
            log.info("%s %s -> %s (%.2f ms)", request.method, request.url.path, status_code, took_ms)


class TelegramAuthMiddleware(BaseHTTPMiddleware):
    """
    PROD: требует X-Telegram-Init-Data для /api/v1/*
    DEV: НЕ требует initData (чтобы работали X-Telegram-Id / DEV_DEFAULT_TELEGRAM_ID через deps.py)
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        # OPTIONS всегда пропускаем
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        path = request.url.path or ""

        # DEV: полностью пропускаем, дальше разрулит deps.py
        if _dev_mode_enabled():
            return await call_next(request)

        # PROD: для API требуем initData
        if path.startswith("/api/v1"):
            init_data = request.headers.get("X-Telegram-Init-Data")
            if not init_data:
                return _unauthorized("X-Telegram-Init-Data")

        return await call_next(request)


# -------------------------------------------------------------------
# BACKWARD COMPATIBILITY (чтобы старые импорты не падали)
# -------------------------------------------------------------------
# Некоторые роуты у тебя импортируют get_current_user из middleware.
# Реэкспортируем правильные зависимости из deps.py.
from app.core.deps import (  # noqa: E402
    get_current_user,
    get_current_user_optional,
    require_admin,
)

# На случай если где-то импортировали старые имена:
LoggingMiddleware = RequestLoggingMiddleware
