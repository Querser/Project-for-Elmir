# app/api/v1/admin_billing.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session, get_current_user
from app.core.exceptions import AppException, ErrorCode
from app.core.responses import success_response
from app.models.user import User
from app.schemas.ban import BanResponse, BanListResponse, BanCreateRequest
from app.schemas.debt import DebtResponse, DebtListResponse
from app.services.ban_service import (
    list_bans,
    manual_ban_user,
    manual_unban_user,
    unban_user_if_no_open_debts,
)
from app.services.debt_service import close_debt, list_debts

router = APIRouter(prefix="/admin", tags=["admin-billing"])


async def get_current_admin(
    current_user: User | None = Depends(get_current_user),
) -> User:
    """
    Общий dependency: проверка, что пользователь — админ.
    """
    if current_user is None:
        raise AppException(
            ErrorCode.UNAUTHORIZED,
            "Пользователь не авторизован через Telegram",
        )
    if not current_user.is_admin:
        raise AppException(
            ErrorCode.FORBIDDEN,
            "Только администратор может выполнять это действие",
        )
    return current_user


# ---------- ДОЛГИ ----------


@router.get("/debts")
async def list_debts_admin(
    user_id: int | None = Query(default=None),
    is_closed: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_admin),
):
    debts, total = await list_debts(
        db,
        user_id=user_id,
        is_closed=is_closed,
        limit=limit,
        offset=offset,
    )
    dto = DebtListResponse(
        items=[DebtResponse.model_validate(d) for d in debts],
        total=total,
        limit=limit,
        offset=offset,
    )
    return success_response(dto.model_dump())


@router.post("/debts/{debt_id}/close")
async def close_debt_admin(
    debt_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_admin),
):
    debt = await close_debt(
        db,
        debt_id=debt_id,
        auto_unban_callback=unban_user_if_no_open_debts,
    )
    dto = DebtResponse.model_validate(debt)
    return success_response(dto.model_dump())


# ---------- БАНЫ ----------


@router.get("/bans")
async def list_bans_admin(
    user_id: int | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_admin),
):
    bans, total = await list_bans(
        db,
        user_id=user_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    dto = BanListResponse(
        items=[BanResponse.model_validate(b) for b in bans],
        total=total,
        limit=limit,
        offset=offset,
    )
    return success_response(dto.model_dump())


@router.post("/bans/{user_id}/ban")
async def manual_ban_admin(
    user_id: int,
    body: BanCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_admin),
):
    ban = await manual_ban_user(db, user_id=user_id, reason=body.reason)
    dto = BanResponse.model_validate(ban)
    return success_response(dto.model_dump())


@router.post("/bans/{user_id}/unban")
async def manual_unban_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_admin),
):
    bans = await manual_unban_user(db, user_id=user_id)
    dto_items = [BanResponse.model_validate(b) for b in bans]
    dto = BanListResponse(
        items=dto_items,
        total=len(dto_items),
        limit=len(dto_items),
        offset=0,
    )
    return success_response(dto.model_dump())
