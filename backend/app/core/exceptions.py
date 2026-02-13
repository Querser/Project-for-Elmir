from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.exceptions")


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return _json_safe(getattr(value, "value", str(value)))
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    # Для Exception и любых не-serializable объектов.
    return str(value)


class ErrorCode(str, Enum):
    # common
    INTERNAL_ERROR = "internal_error"
    VALIDATION_ERROR = "validation_error"
    FORBIDDEN = "forbidden"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"

    # domain
    USER_NOT_FOUND = "user_not_found"
    TRAINING_NOT_FOUND = "training_not_found"
    TRAINING_CANCELLED = "training_cancelled"
    TRAINING_FULL = "training_full"

    ENROLLMENT_NOT_FOUND = "enrollment_not_found"
    ALREADY_ENROLLED = "already_enrolled"

    PAYMENT_NOT_FOUND = "payment_not_found"
    DEBT_NOT_FOUND = "debt_not_found"
    BAN_NOT_FOUND = "ban_not_found"
    SETTING_NOT_FOUND = "setting_not_found"
    PRICE_TIER_NOT_FOUND = "price_tier_not_found"
    LOCATION_NOT_FOUND = "location_not_found"
    RATING_NOT_FOUND = "rating_not_found"


def _code_to_str(code: Any) -> str:
    if code is None:
        return ErrorCode.INTERNAL_ERROR.value
    if isinstance(code, ErrorCode):
        return code.value
    if isinstance(code, Enum):
        return str(getattr(code, "value", str(code)))
    return str(code)


def _http_status_to_error_code(status_code: int) -> str:
    if status_code == 401:
        return ErrorCode.UNAUTHORIZED.value
    if status_code == 403:
        return ErrorCode.FORBIDDEN.value
    if status_code == 404:
        return ErrorCode.NOT_FOUND.value
    if status_code == 409:
        return ErrorCode.CONFLICT.value
    if status_code == 422:
        return ErrorCode.VALIDATION_ERROR.value
    if 400 <= status_code < 500:
        return ErrorCode.CONFLICT.value
    return ErrorCode.INTERNAL_ERROR.value


@dataclass
class AppErrorPayload:
    code: str
    message: str
    details: Optional[Any] = None

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            data["details"] = self.details
        return data


class AppException(Exception):
    """
    Единый формат ошибок приложения.
    """

    def __init__(self, *, status_code: int, code: Any, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = int(status_code)
        self.code = _code_to_str(code)
        self.message = str(message)
        self.details = details

    def payload(self) -> AppErrorPayload:
        return AppErrorPayload(code=self.code, message=self.message, details=self.details)

    # -------- фабрики --------

    @classmethod
    def bad_request(cls, code: Any = ErrorCode.VALIDATION_ERROR, message: str = "Bad request", details: Any = None):
        return cls(status_code=400, code=code, message=message, details=details)

    @classmethod
    def validation(cls, message: str = "Validation error", details: Any = None, code: Any = ErrorCode.VALIDATION_ERROR):
        return cls(status_code=422, code=code, message=message, details=details)

    @classmethod
    def unauthorized(cls, message: str = "Unauthorized", details: Any = None, code: Any = ErrorCode.UNAUTHORIZED):
        return cls(status_code=401, code=code, message=message, details=details)

    @classmethod
    def forbidden(cls, message: str = "Forbidden", details: Any = None, code: Any = ErrorCode.FORBIDDEN):
        return cls(status_code=403, code=code, message=message, details=details)

    @classmethod
    def not_found(cls, code: Any = ErrorCode.NOT_FOUND, message: str = "Not found", details: Any = None):
        return cls(status_code=404, code=code, message=message, details=details)

    @classmethod
    def conflict(cls, code: Any = ErrorCode.CONFLICT, message: str = "Conflict", details: Any = None):
        return cls(status_code=409, code=code, message=message, details=details)

    @classmethod
    def internal(cls, message: str = "Internal server error", details: Any = None, code: Any = ErrorCode.INTERNAL_ERROR):
        return cls(status_code=500, code=code, message=message, details=details)


def setup_exception_handlers(app) -> None:
    """
    Регистрирует обработчики исключений в FastAPI приложении.
    """

    @app.exception_handler(AppException)
    async def _app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.payload().as_dict()},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        details = _json_safe(exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "Validation error",
                    "details": details,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
        status = int(getattr(exc, "status_code", 500) or 500)
        detail = getattr(exc, "detail", None)

        # detail может быть str/dict/Any — приведём аккуратно
        if isinstance(detail, str):
            message = detail
            details = None
        else:
            message = "HTTP error"
            details = detail

        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": _http_status_to_error_code(status),
                    "message": message,
                    **({"details": details} if details is not None else {}),
                }
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                }
            },
        )
