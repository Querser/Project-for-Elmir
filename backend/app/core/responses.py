# app/core/responses.py
"""
Общий формат ответов API.

Успех:
{
  "ok": true,
  "result": {...}
}

Ошибка:
{
  "ok": false,
  "error": {
    "code": "SOME_ERROR_CODE",
    "message": "Человекочитаемое сообщение",
    "details": {...}  # необязательно
  }
}
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import status
from fastapi.responses import JSONResponse


def success_response(data: Any, status_code: int = status.HTTP_200_OK) -> JSONResponse:
    """Обёртка для успешных ответов."""
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": True,
            "result": data,
        },
    )


def error_response(
    *,
    error_code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[dict[str, Any]] = None,
) -> JSONResponse:
    """Обёртка для ответов с ошибкой."""
    payload: dict[str, Any] = {
        "ok": False,
        "error": {
            "code": error_code,
            "message": message,
        },
    }
    if details:
        payload["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=payload)
