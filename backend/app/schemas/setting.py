from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SettingUpsertRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=150)
    value: str = Field(..., min_length=0)
    description: Optional[str] = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class SettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str
    description: Optional[str] = None


class SettingListResponse(BaseModel):
    items: List[SettingResponse]
    total: int = 0
    limit: int = 50
    offset: int = 0
