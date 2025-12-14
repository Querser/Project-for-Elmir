# app/core/middleware.py

from __future__ import annotations

import logging
import time
from typing import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.telegram_auth import (
    TelegramAuthError,
    get_or_create_user,
    parse_and_validate_init_data,
)
from app.db.session import SessionLocal
from app.models import User

logger = logging.getLogger("app.middleware")

# Название заголовка, в который фронтенд будет присылать initData
TELEGRAM_INIT_HEADER = "X-Telegram-Init-Data"

# Пути, где не нужна авторизация и не надо трогать initData
UNPROTECTED_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class TelegramAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware для авторизации через Telegram Mini App.

    Если в заголовке X-Telegram-Init-Data переданы корректные данные:
    - валидируем подпись;
    - создаём/обновляем пользователя в БД;
    - сохраняем его в request.state.user.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable]
    ):
        path = request.url.path
        request.state.user = None

        # Пропускаем технические эндпоинты
        if path in UNPROTECTED_PATHS or path.startswith("/docs") or path.startswith(
            "/openapi"
        ):
            return await call_next(request)

        init_data = request.headers.get(TELEGRAM_INIT_HEADER)
        if not init_data:
            # Для части эндпоинтов Telegram-авторизация не нужна.
            return await call_next(request)

        db = SessionLocal()
        try:
            tg_init = parse_and_validate_init_data(
                init_data=init_data, bot_token=self.settings.telegram_bot_token
            )
            user = get_or_create_user(db, tg_init)
            db.commit()
            db.refresh(user)
            request.state.user = user
        except TelegramAuthError as exc:
            db.rollback()
            logger.warning("Telegram auth error on %s: %s", path, exc.message)
        except Exception:
            db.rollback()
            logger.exception("Unexpected error during Telegram auth on %s", path)
        finally:
            db.close()

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Простое логирование каждого HTTP-запроса.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable]
    ):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000.0

        user_id = getattr(getattr(request.state, "user", None), "id", None)

        logger.info(
            "%s %s status=%s duration_ms=%.2f user_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            user_id,
        )

        return response


async def get_current_user(request: Request) -> User:
    """
    Dependency для защищённых endpoint'ов.

    Если request.state.user не установлен — считаем, что пользователь не авторизован.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise AppException(
            error_code="UNAUTHORIZED",
            message="Пользователь не авторизован через Telegram",
            status_code=401,
        )
    return user
