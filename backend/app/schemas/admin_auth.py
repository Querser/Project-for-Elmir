from __future__ import annotations

from pydantic import BaseModel, Field


class AdminLoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class AdminRefreshIn(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class AdminTokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_in: int


class AdminMeOut(BaseModel):
    username: str
