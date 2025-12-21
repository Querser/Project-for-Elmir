# backend/app/schemas/debt.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.debt import DebtStatus


class DebtRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    training_id: int
    amount: Decimal
    status: DebtStatus
    created_at: datetime
    closed_at: datetime | None = None
    closed_by_user_id: int | None = None
    close_reason: str | None = None


class DebtCloseRequest(BaseModel):
    close_reason: str | None = None
