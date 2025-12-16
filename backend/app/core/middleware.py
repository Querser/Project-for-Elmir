from __future__ import annotations

import logging
import time
from typing import Callable, Awaitable

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.telegram_auth import (
    TelegramAuthError,
    validate_telegram_init_data,
)
from app.db.session import SessionLocal
from app.models.user import User
from app.services.user_service import get_or_create_user_from_telegram

logger = logging.getLogger("app.middleware")


# --------- Логирование запросов --------- #
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Простое логирование запросов/ответов:
    метод, путь, статус, время обработки.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error for %s %s", request.method, path)
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.2f ms)",
            request.method,
            path,
            response.status_code,
            duration_ms,
        )
        return response


# --------- Telegram WebApp авторизация --------- #
class TelegramAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware, который:
    - читает заголовок X-Telegram-Init-Data
    - валидирует подпись Telegram
    - создаёт/обновляет пользователя в БД
    - кладёт User в request.state.user
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:  # type: ignore[override]
        # По умолчанию пользователя нет
        request.state.user = None

        path = request.url.path

        # Разрешаем технические эндпоинты без авторизации
        if path in ("/health", "/api/v1/ping"):
            return await call_next(request)

        init_data = request.headers.get("X-Telegram-Init-Data")
        if not init_data:
            # Нет Telegram-данных — запрос не авторизован,
            # но сам эндпоинт решает, критично это или нет.
            return await call_next(request)

        bot_token = settings.telegram_bot_token
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не задан, Telegram-авторизация невозможна")
            return await call_next(request)

        # Валидируем initData
        try:
            tg_init = validate_telegram_init_data(
                init_data=init_data,
                bot_token=bot_token,
                max_age_seconds=24 * 60 * 60,
            )
        except TelegramAuthError as exc:
            logger.warning(
                "Telegram auth error on %s: %s",
                path,
                exc.message,
            )
            # Пользователь не считается авторизованным
            return await call_next(request)
        except Exception:
            logger.exception("Unexpected error while validating Telegram initData")
            return await call_next(request)

        if not tg_init.user or "id" not in tg_init.user:
            logger.warning("Telegram initData does not contain 'user.id'")
            return await call_next(request)

        tg_user = tg_init.user

        # Создаём / обновляем пользователя в БД
        try:
            with SessionLocal() as db:
                user = get_or_create_user_from_telegram(
                    db=db,
                    telegram_id=tg_user["id"],
                    username=tg_user.get("username"),
                    first_name=tg_user.get("first_name"),
                    last_name=tg_user.get("last_name"),
                    phone=None,  # на будущее, если решим брать телефон
                )
                request.state.user = user
        except Exception:
            logger.exception("Error while getting/creating user from Telegram initData")
            request.state.user = None

        return await call_next(request)


# --------- Зависимость для эндпоинтов --------- #
async def get_current_user(request: Request) -> User:
    """
    FastAPI-зависимость. Используется как Depends(get_current_user).

    Если пользователь не авторизован через Telegram, бросаем AppException
    с кодом UNAUTHORIZED.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise AppException(
            error_code="UNAUTHORIZED",
            message="Пользователь не авторизован через Telegram",
            status_code=401,
        )
    return user
