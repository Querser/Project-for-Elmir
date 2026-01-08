from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PriceTierUpsertRequest(BaseModel):
    """
    Incoming tier definition.

    min_level_id / max_level_id define an inclusive range of user levels.
    Use NULL for open-ended bounds.
    """

    label: Optional[str] = Field(default=None, max_length=255)
    min_level_id: Optional[int] = Field(default=None, ge=1)
    max_level_id: Optional[int] = Field(default=None, ge=1)
    price: float = Field(..., gt=0)


class PriceTierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: Optional[str] = None

    min_level_id: Optional[int] = None
    max_level_id: Optional[int] = None

    min_level_name: Optional[str] = None
    max_level_name: Optional[str] = None

    price: float
