# app/schemas/debt.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DebtResponse(BaseModel):
    id: int
    user_id: int
    training_id: int | None
    amount: float
    description: str | None
    is_auto: bool
    is_closed: bool
    created_at: datetime
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DebtListResponse(BaseModel):
    items: list[DebtResponse]
    total: int
    limit: int
    offset: int
