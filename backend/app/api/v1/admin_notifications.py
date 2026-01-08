from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user
from app.core.responses import success_response
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    AdminBroadcastNotificationIn,
    AdminCreateNotificationsForTrainingIn,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


@router.post("/broadcast", response_model=dict)
def broadcast(payload: AdminBroadcastNotificationIn, db: Session = Depends(get_db), _: User = Depends(get_current_admin_user)):
    created = NotificationService.broadcast_notification(db, payload)
    return success_response({"created": created})


@router.post("/training", response_model=dict)
def notify_training(payload: AdminCreateNotificationsForTrainingIn, db: Session = Depends(get_db), _: User = Depends(get_current_admin_user)):
    created = NotificationService.notify_training_participants(db, payload)
    return success_response({"created": created})
