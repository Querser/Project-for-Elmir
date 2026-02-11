from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends

from app.core.exceptions import AppException, ErrorCode
from app.core.admin_tokens import (
    issue_admin_tokens,
    verify_admin_access_token,
    verify_admin_refresh_token,
    AdminTokenError,
)
from app.schemas.admin_auth import AdminLoginIn, AdminRefreshIn, AdminTokensOut, AdminMeOut

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


def _strip_wrapping_quotes(value: str) -> str:
    v = (value or "").strip()
    while len(v) >= 2 and v[0] == v[-1] and v[0] in {"'", '"'}:
        v = v[1:-1].strip()
    return v


def _env(name: str) -> str:
    return _strip_wrapping_quotes(os.getenv(name) or "")


@router.post("/login", response_model=AdminTokensOut)
def admin_login(payload: AdminLoginIn) -> AdminTokensOut:
    username = _env("ADMIN_USERNAME")
    password = _env("ADMIN_PASSWORD")

    if not username or not password:
        raise AppException.internal(
            message="Admin credentials are not configured",
            details={"missing": ["ADMIN_USERNAME", "ADMIN_PASSWORD"]},
        )

    ok = hmac.compare_digest(payload.username, username) and hmac.compare_digest(payload.password, password)
    if not ok:
        raise AppException.unauthorized(
            code=ErrorCode.UNAUTHORIZED,
            message="Неверный логин или пароль",
        )

    tokens = issue_admin_tokens(username=username)
    return AdminTokensOut(**tokens)


@router.post("/refresh", response_model=AdminTokensOut)
def admin_refresh(payload: AdminRefreshIn) -> AdminTokensOut:
    try:
        data = verify_admin_refresh_token(payload.refresh_token)
    except AdminTokenError:
        raise AppException.unauthorized(message="Неверный или просроченный refresh token")

    username = str(data.get("username") or "admin")
    tokens = issue_admin_tokens(username=username)
    return AdminTokensOut(**tokens)


@router.get("/me", response_model=AdminMeOut)
def admin_me(authorization: str = "") -> AdminMeOut:
    """
    Лёгкий endpoint для проверки access токена.
    """
    auth = (authorization or "").strip()
    # FastAPI не прокинет автоматически Authorization сюда без зависимости,
    # поэтому этот endpoint обычно будет использоваться через JS fetch с заголовком.
    # Если хочешь строго — лучше использовать Depends(get_current_admin_principal) из deps.py.
    if not auth.lower().startswith("bearer "):
        raise AppException.unauthorized(message="Требуется Authorization: Bearer <access_token>")

    token = auth[7:].strip()
    try:
        payload = verify_admin_access_token(token)
    except AdminTokenError:
        raise AppException.unauthorized(message="Неверный или просроченный access token")

    return AdminMeOut(username=str(payload.get("username") or "admin"))
