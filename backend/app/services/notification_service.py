"""
Notification services (sync).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    AdminBroadcastNotificationIn,
    AdminCreateNotificationsForTrainingIn,
)


class NotificationService:
    @staticmethod
    def list_user_notifications(db: Session, user_id: int, limit: int = 50, offset: int = 0):
        q = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        total = q.count()
        items = q.offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def mark_notification_read(db: Session, user_id: int, notification_id: int) -> bool:
        notif = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if not notif:
            return False
        notif.is_read = True
        db.add(notif)
        db.commit()
        return True

    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        type_: str,
        title: str,
        text: str,
        url: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> Notification:
        n = Notification(
            user_id=user_id,
            type=type_,
            title=title,
            body=text,
            text=text,
            url=url,
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
        )
        db.add(n)
        db.commit()
        db.refresh(n)
        return n

    @staticmethod
    def broadcast_notification(db: Session, payload: AdminBroadcastNotificationIn) -> int:
        user_ids = [u for (u,) in db.query(User.id).all()]
        objs = [
            Notification(
                user_id=uid,
                type=payload.type,
                title=payload.title,
                body=payload.text,
                text=payload.text,
                url=payload.url,
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
            )
            for uid in user_ids
        ]
        if objs:
            db.bulk_save_objects(objs)
            db.commit()
        return len(objs)

    @staticmethod
    def notify_training_participants(db: Session, payload: AdminCreateNotificationsForTrainingIn) -> int:
        ids = (
            db.query(Enrollment.user_id)
            .filter(
                Enrollment.training_id == payload.training_id,
                Enrollment.status.in_([EnrollmentStatus.CONFIRMED, EnrollmentStatus.RESERVE]),
            )
            .distinct()
            .all()
        )
        user_ids = [u for (u,) in ids]

        objs = [
            Notification(
                user_id=uid,
                type=payload.type,
                title=payload.title,
                body=payload.text,
                text=payload.text,
                url=payload.url,
                entity_type="training",
                entity_id=payload.training_id,
            )
            for uid in user_ids
        ]
        if objs:
            db.bulk_save_objects(objs)
            db.commit()
        return len(objs)
