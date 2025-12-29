# backend/app/api/v1/notifications.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.schemas.notification import NotificationListOut
from app.services.notification_service import list_user_notifications, mark_notification_read

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=dict)
async def get_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items, total = await list_user_notifications(db, user_id=current_user.id, limit=limit, offset=offset)
    return {"ok": True, "result": NotificationListOut(items=items, total=total, limit=limit, offset=offset), "error": None}


@router.post("/{notification_id}/read", response_model=dict)
async def read_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ok = await mark_notification_read(db, user_id=current_user.id, notification_id=notification_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"ok": True, "result": True, "error": None}
