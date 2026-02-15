from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user_any, get_db
from app.core.responses import success_response
from app.schemas.admin_user import AdminSetLevelRequest
from app.services.audit_log_service import write_audit_log
from app.services.admin_user_service import (
    cancel_user_active_enrollments,
    get_admin_user_details,
    list_admin_users,
    mark_debt_paid_offline,
    set_user_level,
)
from app.services.admin_export_service import (
    build_payments_export_last_quarter_xlsx,
    build_users_export_xlsx,
)
from app.services.ban_service import manual_ban_user, unban_user

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class AdminBanRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    until: datetime | None = None


def _xlsx_response(content: bytes, filename: str, *, extra_headers: dict[str, str] | None = None) -> StreamingResponse:
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
    }
    if extra_headers:
        headers.update(extra_headers)

    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


def _actor_payload(actor: Any) -> tuple[int | None, str]:
    actor_id = None
    if hasattr(actor, "id"):
        try:
            actor_id = int(getattr(actor, "id"))
        except Exception:
            actor_id = None

    actor_name = (
        getattr(actor, "username", None)
        or getattr(actor, "first_name", None)
        or "admin"
    )
    return actor_id, str(actor_name)


@router.get("/export/users.xlsx")
def export_users_admin(
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    content = build_users_export_xlsx(db)
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_EXPORT_USERS_XLSX",
        entity="user",
        entity_id=None,
        data={"actor": actor_name, "format": "xlsx"},
    )
    filename = f"users-export-{datetime.utcnow():%Y%m%d-%H%M%S}.xlsx"
    return _xlsx_response(content, filename)


@router.get("/export/payments.xlsx")
def export_payments_admin(
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    content, deleted_old = build_payments_export_last_quarter_xlsx(db)
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_EXPORT_PAYMENTS_XLSX",
        entity="payment",
        entity_id=None,
        data={
            "actor": actor_name,
            "format": "xlsx",
            "period": "last_quarter",
            "deleted_old_records": int(deleted_old or 0),
        },
    )
    filename = f"payments-last-quarter-{datetime.utcnow():%Y%m%d-%H%M%S}.xlsx"
    return _xlsx_response(
        content,
        filename,
        extra_headers={"X-Purged-Payments": str(int(deleted_old or 0))},
    )


@router.get("", response_model=dict)
def list_users_admin(
    q: str | None = Query(default=None),
    user_id: int | None = Query(default=None, ge=1),
    level_id: int | None = Query(default=None),
    is_banned: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user_any),
):
    items, total = list_admin_users(
        db,
        q=q,
        user_id=user_id,
        level_id=level_id,
        is_banned=is_banned,
        limit=limit,
        offset=offset,
    )
    return success_response({"items": items, "total": total, "limit": limit, "offset": offset})


@router.get("/{user_id}", response_model=dict)
def get_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user_any),
):
    result = get_admin_user_details(db, user_id=user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return success_response(result)


@router.patch("/{user_id}/level", response_model=dict)
def set_level_admin(
    user_id: int,
    payload: AdminSetLevelRequest,
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    user = set_user_level(db, user_id=user_id, level_id=payload.level_id)
    if not user:
        raise HTTPException(status_code=404, detail="User or level not found")
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_SET_USER_LEVEL",
        entity="user",
        entity_id=user.id,
        data={"actor": actor_name, "target_user_id": user.id, "level_id": user.level_id},
    )
    return success_response({"user_id": user.id, "level_id": user.level_id})


@router.post("/{user_id}/ban", response_model=dict)
def ban_user_admin(
    user_id: int,
    payload: AdminBanRequest,
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    ban = manual_ban_user(db, user_id=user_id, reason=payload.reason, until=payload.until)
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_BAN_USER",
        entity="ban",
        entity_id=ban.id,
        data={
            "actor": actor_name,
            "target_user_id": user_id,
            "ban_type": ban.type.value if hasattr(ban.type, "value") else str(ban.type),
            "reason": payload.reason,
            "until": payload.until.isoformat() if payload.until else None,
        },
    )
    return success_response(
        {
            "id": ban.id,
            "user_id": ban.user_id,
            "type": ban.type.value if hasattr(ban.type, "value") else str(ban.type),
            "reason": ban.reason,
            "active": bool(ban.active),
            "until": ban.until,
        }
    )


@router.post("/{user_id}/unban", response_model=dict)
def unban_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    affected = unban_user(db, user_id=user_id)
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_UNBAN_USER",
        entity="user",
        entity_id=user_id,
        data={"actor": actor_name, "target_user_id": user_id, "updated": affected},
    )
    return success_response({"updated": affected})


@router.post("/{user_id}/cancel-enrollments", response_model=dict)
def cancel_user_enrollments_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    result = cancel_user_active_enrollments(
        db,
        user_id=user_id,
        require_active_ban=True,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")

    cancelled_count, has_active_ban = result
    if not has_active_ban:
        raise HTTPException(
            status_code=409,
            detail="Пользователь не находится в активном бане",
        )

    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_CANCEL_BANNED_USER_ENROLLMENTS",
        entity="user",
        entity_id=user_id,
        data={
            "actor": actor_name,
            "target_user_id": user_id,
            "cancelled_enrollments": cancelled_count,
        },
    )
    return success_response({"user_id": user_id, "cancelled": cancelled_count})


@router.post("/{user_id}/debts/{debt_id}/mark-paid", response_model=dict)
def mark_paid_offline_admin(
    user_id: int,
    debt_id: int,
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    debt = mark_debt_paid_offline(db, user_id=user_id, debt_id=debt_id)
    if debt is None:
        raise HTTPException(status_code=404, detail="Debt not found")
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_MARK_DEBT_PAID_OFFLINE",
        entity="debt",
        entity_id=debt.id,
        data={
            "actor": actor_name,
            "target_user_id": user_id,
            "debt_id": debt.id,
            "training_id": debt.training_id,
            "status": debt.status.value if hasattr(debt.status, "value") else str(debt.status),
        },
    )

    return success_response(
        {
            "id": debt.id,
            "user_id": debt.user_id,
            "training_id": debt.training_id,
            "status": debt.status.value if hasattr(debt.status, "value") else str(debt.status),
            "closed_at": debt.closed_at,
        }
    )
