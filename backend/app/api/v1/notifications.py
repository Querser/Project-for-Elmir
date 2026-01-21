from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import success_response
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationListOut
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=dict)
def get_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = NotificationService.list_user_notifications(db, current_user.id, limit, offset)
    return success_response(NotificationListOut(items=items, total=total, limit=limit, offset=offset))



@router.post("/{notification_id}/read", response_model=dict)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = NotificationService.mark_notification_read(db, current_user.id, notification_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return success_response({"ok": True})
