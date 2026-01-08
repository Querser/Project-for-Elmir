from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(str, Enum):
    # common
    INTERNAL_ERROR = "internal_error"
    VALIDATION_ERROR = "validation_error"
    FORBIDDEN = "forbidden"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"

    # domain (покрываем всё, что часто встречается в проекте)
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
        # на случай если где-то другой Enum
        return str(getattr(code, "value", str(code)))
    return str(code)


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
    Импортируется из app.main как:
        from app.core.exceptions import setup_exception_handlers
    """

    @app.exception_handler(AppException)
    async def _app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.payload().as_dict()},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "Validation error",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
        # чтобы HTTPException тоже был в едином формате
        status = int(getattr(exc, "status_code", 500) or 500)
        detail = getattr(exc, "detail", None)
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": ErrorCode.CONFLICT.value if status == 409 else ErrorCode.INTERNAL_ERROR.value,
                    "message": str(detail) if detail is not None else "HTTP error",
                }
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                }
            },
        )
