from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.debt import DebtStatus


class DebtResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    training_id: int
    amount: Decimal
    status: DebtStatus
    created_at: datetime
    closed_at: Optional[datetime] = None


class DebtListResponse(BaseModel):
    items: List[DebtResponse]
    total: int = 0
    limit: int = 50
    offset: int = 0


class DebtCreateRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    training_id: int = Field(..., ge=1)
    amount: Decimal = Field(..., gt=0)
