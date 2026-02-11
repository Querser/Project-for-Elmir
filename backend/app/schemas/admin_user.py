from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AdminUserListItem(BaseModel):
    id: int
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    level_id: Optional[int] = None
    level_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    has_active_ban: bool
    open_debts_count: int


class AdminUsersListResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int
    limit: int
    offset: int


class AdminUserTrainingHistoryItem(BaseModel):
    enrollment_id: int
    training_id: int
    status: str
    is_reserve: bool
    is_paid: bool
    created_at: datetime
    training_title: Optional[str] = None
    training_start_at: Optional[datetime] = None
    coach_name: Optional[str] = None
    location_id: Optional[int] = None


class AdminUserDebtItem(BaseModel):
    id: int
    training_id: int
    amount: Any
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None


class AdminUserBanItem(BaseModel):
    id: int
    type: str
    reason: str
    active: bool
    created_at: datetime
    until: Optional[datetime] = None


class AdminUserDetailsResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[Any] = None
    level_id: Optional[int] = None
    level_name: Optional[str] = None
    rating: int
    cups: int
    is_active: bool
    is_admin: bool
    has_active_ban: bool
    open_debts_count: int
    training_history: list[AdminUserTrainingHistoryItem]
    current_debts: list[AdminUserDebtItem]
    bans: list[AdminUserBanItem]


class AdminSetLevelRequest(BaseModel):
    level_id: Optional[int] = None
