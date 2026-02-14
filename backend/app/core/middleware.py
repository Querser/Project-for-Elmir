# app/core/middleware.py
from __future__ import annotations

import logging
import os
import re
import time
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.services.metrics_service import MetricsService

log = logging.getLogger("app.middleware")

_TRAINING_CALENDAR_ICS_RE = re.compile(r"^/api/v1/trainings/\d+/calendar\.ics/?$")
_TELEGRAM_WEBHOOK_PATHS = {"/api/v1/telegram/webhook", "/api/v1/telegram/webhook/"}


def _env_truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip().strip('"').strip("'").lower()
    return v in {"1", "true", "yes", "y", "on"}


def _is_dev_env() -> bool:
    env = (os.getenv("ENVIRONMENT") or "").strip().strip('"').strip("'").lower()
    return env in {"dev", "development", "local"}


def _dev_mode_enabled() -> bool:
    if _env_truthy("ALLOW_INSECURE_HEADER_AUTH", False):
        return True
    if _env_truthy("DEV_AUTO_CREATE_USER_FROM_HEADER", False):
        return True
    if _is_dev_env():
        return True
    return False


def _unauthorized(required_header: str = "X-Telegram-Init-Data") -> JSONResponse:
    return JSONResponse(
        {
            "error": {
                "code": "unauthorized",
                "message": "Пользователь не авторизован",
                "details": {"required_header": required_header},
            }
        },
        status_code=401,
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        start = time.perf_counter()
        response: Optional[Response] = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            MetricsService.record_exception()
            raise
        finally:
            took_ms = (time.perf_counter() - start) * 1000.0
            status_code = getattr(response, "status_code", 500)
            MetricsService.record_http_status(status_code)
            log.info("%s %s -> %s (%.2f ms)", request.method, request.url.path, status_code, took_ms)


class TelegramAuthMiddleware(BaseHTTPMiddleware):
    """
    PROD:
      - требует X-Telegram-Init-Data для /api/v1/*

    ИСКЛЮЧЕНИЯ (чтобы админка работала по токенам):
      - /api/v1/admin/auth/* (логин/рефреш)
      - любые запросы с Authorization: Bearer ...
    DEV:
      - полностью пропускаем (дальше разрулит deps.py)
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        path = request.url.path or ""

        # public endpoints:
        # - Telegram webhook (Bot API)
        # - training calendar ICS file (opened by external calendar apps)
        if path in _TELEGRAM_WEBHOOK_PATHS or _TRAINING_CALENDAR_ICS_RE.match(path):
            return await call_next(request)

        # DEV: пропускаем всё
        if _dev_mode_enabled():
            return await call_next(request)

        # allow admin auth endpoints
        if path.startswith("/api/v1/admin/auth"):
            return await call_next(request)

        # allow bearer-token requests (admin panel)
        auth = (request.headers.get("Authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            return await call_next(request)

        # PROD: для остальных API требуем initData
        if path.startswith("/api/v1"):
            init_data = request.headers.get("X-Telegram-Init-Data")
            if not init_data:
                return _unauthorized("X-Telegram-Init-Data")

        return await call_next(request)


# -------------------------------------------------------------------
# BACKWARD COMPATIBILITY
# -------------------------------------------------------------------
from app.core.deps import (  # noqa: E402
    get_current_user,
    get_current_user_optional,
    require_admin,
)

LoggingMiddleware = RequestLoggingMiddleware
