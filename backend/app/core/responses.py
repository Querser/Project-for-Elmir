# backend/app/core/responses.py
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK


def success_response(
    result: Any = None,
    status_code: int = HTTP_200_OK,
) -> JSONResponse:
    """
    Обёртка для успешного ответа в едином формате:
    {
      "ok": true,
      "result": ...
    }
    jsonable_encoder конвертирует datetime/date/Decimal в JSON-совместимый вид.
    """
    payload: Dict[str, Any] = {"ok": True}
    if result is not None:
        payload["result"] = result

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
    )


def error_response(
    *,
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[dict] = None,
) -> JSONResponse:
    """
    Обёртка для ошибок:
    {
      "ok": false,
      "error": {
        "code": "...",
        "message": "...",
        "details": { ... }  # опционально
      }
    }
    """
    error_obj: Dict[str, Any] = {
        "code": error_code,
        "message": message,
    }
    if details is not None:
        error_obj["details"] = details

    payload = {
        "ok": False,
        "error": error_obj,
    }

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
    )
