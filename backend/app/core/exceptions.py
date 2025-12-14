# app/core/exceptions.py

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses import error_response

logger = logging.getLogger("app.errors")


class AppException(Exception):
    """
    Базовое прикладное исключение.

    Используем его, когда хотим вернуть осмысленную ошибку клиенту.
    """

    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Регистрируем глобальные обработчики ошибок на FastAPI-приложении.
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            "AppException: %s %s -> %s (%s)",
            request.method,
            request.url.path,
            exc.error_code,
            exc.message,
            extra={"details": exc.details},
        )
        return error_response(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            "ValidationError: %s %s -> %s",
            request.method,
            request.url.path,
            exc.errors(),
        )
        return error_response(
            error_code="VALIDATION_ERROR",
            message="Некорректные данные запроса",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(
            "HTTPException: %s %s -> %s",
            request.method,
            request.url.path,
            exc.detail,
        )
        return error_response(
            error_code="HTTP_ERROR",
            message=str(exc.detail),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception for %s %s",
            request.method,
            request.url.path,
        )
        return error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message="Внутренняя ошибка сервера",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
