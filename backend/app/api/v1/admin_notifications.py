from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin
from app.schemas.notification import AdminBroadcastNotificationIn, AdminTrainingNotificationIn
from app.services.audit_log_service import write_audit_log
from app.services.notification_service import broadcast_notification, create_notifications_for_training

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


@router.post("/broadcast", response_model=dict)
async def admin_broadcast(
    payload: AdminBroadcastNotificationIn,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
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

    # audit
    await write_audit_log(
        db,
        user_id=getattr(admin, "id", None),
        action="ADMIN_NOTIFICATION_BROADCAST",
        entity="notification",
        entity_id=None,
        data={
            "type": str(payload.type),
            "title": payload.title,
            "entity_type": payload.entity_type,
            "entity_id": payload.entity_id,
            "count": count,
        },
        commit=True,
    )

    return {"ok": True, "result": count, "error": None}


@router.post("/training/{training_id}", response_model=dict)
async def admin_training_notify(
    training_id: int,
    payload: AdminTrainingNotificationIn,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    count = await create_notifications_for_training(
        db,
        training_id=training_id,
        ntype=payload.type,
        text=payload.text,
        title=payload.title,
        url=payload.url,
    )

    # audit
    await write_audit_log(
        db,
        user_id=getattr(admin, "id", None),
        action="ADMIN_NOTIFICATION_TRAINING",
        entity="training",
        entity_id=training_id,
        data={
            "type": str(payload.type),
            "title": payload.title,
            "count": count,
        },
        commit=True,
    )

    return {"ok": True, "result": count, "error": None}
