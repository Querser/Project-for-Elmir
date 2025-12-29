# backend/app/api/v1/admin_notifications.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin
from app.schemas.notification import AdminBroadcastNotificationIn, AdminTrainingNotificationIn
from app.services.notification_service import broadcast_notification, create_notifications_for_training

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


@router.post("/broadcast", response_model=dict)
async def admin_broadcast(
    payload: AdminBroadcastNotificationIn,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    count = await broadcast_notification(
        db,
        ntype=payload.type,
        text=payload.text,
        title=payload.title,
        url=payload.url,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
    )
    return {"ok": True, "result": count, "error": None}


@router.post("/training/{training_id}", response_model=dict)
async def admin_training_notify(
    training_id: int,
    payload: AdminTrainingNotificationIn,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    count = await create_notifications_for_training(
        db,
        training_id=training_id,
        ntype=payload.type,
        text=payload.text,
        title=payload.title,
        url=payload.url,
    )
    if count == 0:
        # Это не ошибка сервера, просто никто не записан / нет enrollments
        return {"ok": True, "result": 0, "error": None}
    return {"ok": True, "result": count, "error": None}
