from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user_any, get_db
from app.core.responses import success_response
from app.schemas.notification import (
    AdminBroadcastNotificationIn,
    AdminCreateNotificationsForTrainingIn,
    AdminUserTargetedNotificationIn,
)
from app.services.audit_log_service import write_audit_log
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


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


@router.post("/broadcast", response_model=dict)
def broadcast(
    payload: AdminBroadcastNotificationIn,
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    created = NotificationService.broadcast_notification(db, payload)
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_NOTIFICATION_BROADCAST",
        entity="notification",
        entity_id=None,
        data={
            "actor": actor_name,
            "type": payload.type,
            "title": payload.title,
            "created": created,
        },
    )
    return success_response({"created": created})


@router.post("/training", response_model=dict)
def notify_training(
    payload: AdminCreateNotificationsForTrainingIn,
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    created = NotificationService.notify_training_participants(db, payload)
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_NOTIFICATION_TRAINING",
        entity="training",
        entity_id=payload.training_id,
        data={
            "actor": actor_name,
            "type": payload.type,
            "title": payload.title,
            "training_id": payload.training_id,
            "created": created,
        },
    )
    return success_response({"created": created})


@router.post("/users", response_model=dict)
def notify_users(
    payload: AdminUserTargetedNotificationIn,
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    created = NotificationService.create_notifications_for_users(db, payload)
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_NOTIFICATION_USERS",
        entity="notification",
        entity_id=None,
        data={
            "actor": actor_name,
            "type": payload.type,
            "title": payload.title,
            "users_count": len(payload.user_ids),
            "created": created,
        },
    )
    return success_response({"created": created})


@router.get("/sent", response_model=dict)
def list_sent(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user_any),
):
    items, total = NotificationService.list_sent_notifications(
        db,
        limit=limit,
        offset=offset,
        type_=type,
        q=q,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )

    result = [
        {
            "id": n.id,
            "user_id": n.user_id,
            "type": n.type,
            "title": n.title,
            "text": n.text,
            "entity_type": n.entity_type,
            "entity_id": n.entity_id,
            "url": n.url,
            "is_read": bool(n.is_read),
            "created_at": n.created_at,
        }
        for n in items
    ]
    return success_response({"items": result, "total": total, "limit": limit, "offset": offset})
