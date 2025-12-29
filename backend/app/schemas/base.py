# backend/app/schemas/base.py
from __future__ import annotations

from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ErrorOut(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = {}


class BaseResponse(BaseModel, Generic[T]):
    ok: bool = True
    result: Optional[T] = None
    error: Optional[ErrorOut] = None

    model_config = ConfigDict(from_attributes=True)
