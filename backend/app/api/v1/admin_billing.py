# app/api/v1/admin_billing.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.exceptions import AppException, ErrorCode
from app.core.responses import success_response
from app.db.session import get_db
from app.models.user import User
from app.schemas.ban import BanCreateRequest, BanListResponse, BanResponse
from app.schemas.debt import DebtListResponse, DebtResponse
from app.services.ban_service import (
    list_bans,
    manual_ban_user,
    manual_unban_user,
    unban_user_if_no_open_debts,
)
from app.services.debt_service import close_debt, list_debts

router = APIRouter(prefix="/admin", tags=["admin-billing"])


def _dump(model):
    # pydantic v2: model_dump, v1: dict
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _validate(model_cls, obj):
    # pydantic v2: model_validate, v1: from_orm
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(obj, from_attributes=True)
    return model_cls.from_orm(obj)


async def get_current_admin(
    current_user: User | None = Depends(get_current_user),
) -> User:
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
    training_id: int | None = Query(default=None),
    is_closed: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    status = None
    if is_closed is True:
        status = "CLOSED"
    elif is_closed is False:
        status = "OPEN"

    debts = list_debts(
        db,
        user_id=user_id,
        training_id=training_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    dto_items = [_validate(DebtResponse, d) for d in debts]

    dto = DebtListResponse(
        items=dto_items,
        total=len(dto_items),
        limit=limit,
        offset=offset,
    )
    return success_response(_dump(dto))


@router.post("/debts/{debt_id}/close")
async def close_debt_admin(
    debt_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    # close_debt может вернуть int  нам это не важно, мы перечитаем долг из БД
    close_debt(
        db,
        debt_id=debt_id,
        auto_unban_callback=unban_user_if_no_open_debts,
    )

    from app.models.debt import Debt

    debt = db.get(Debt, debt_id)
    if debt is None:
        raise AppException(ErrorCode.INTERNAL_SERVER_ERROR, "Долг не найден после закрытия")

    dto = _validate(DebtResponse, debt)
    return success_response(_dump(dto))


# ---------- БАНЫ ----------


@router.get("/bans")
async def list_bans_admin(
    user_id: int | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    # Совместимость: list_bans может ждать active или only_active
    try:
        bans = list_bans(db, user_id=user_id, active=is_active, limit=limit, offset=offset)
    except TypeError:
        bans = list_bans(db, user_id=user_id, only_active=is_active, limit=limit, offset=offset)

    dto_items = [_validate(BanResponse, b) for b in bans]
    dto = BanListResponse(items=dto_items, total=len(dto_items), limit=limit, offset=offset)
    return success_response(_dump(dto))


@router.post("/bans/{user_id}/ban")
async def manual_ban_admin(
    user_id: int,
    body: BanCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ban = manual_ban_user(db, user_id=user_id, reason=body.reason)
    dto = _validate(BanResponse, ban)
    return success_response(_dump(dto))


@router.post("/bans/{user_id}/unban")
async def manual_unban_admin(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    # Чтобы не зависеть от того, возвращает manual_unban_user список или int:
    # 1) запомним активные баны
    try:
        active_before = list_bans(db, user_id=user_id, active=True, limit=10_000, offset=0)
    except TypeError:
        active_before = list_bans(db, user_id=user_id, only_active=True, limit=10_000, offset=0)

    ids = [b.id for b in active_before]

    # 2) снимем бан (что бы ни вернуло  нам ок)
    manual_unban_user(db, user_id=user_id)

    # 3) перечитаем те же записи по ids
    bans = []
    if ids:
        from app.models.ban import Ban

        bans = db.query(Ban).filter(Ban.id.in_(ids)).all()

    dto_items = [_validate(BanResponse, b) for b in bans]
    dto = BanListResponse(items=dto_items, total=len(dto_items), limit=len(dto_items), offset=0)
    return success_response(_dump(dto))
