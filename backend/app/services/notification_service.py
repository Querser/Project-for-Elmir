"""
Notification services (sync).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    AdminBroadcastNotificationIn,
    AdminCreateNotificationsForTrainingIn,
    AdminUserTargetedNotificationIn,
)


class NotificationService:
    DEFAULT_TITLE = "\u0423\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435"

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def list_user_notifications(db: Session, user_id: int, limit: int = 50, offset: int = 0):
        query = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def list_sent_notifications(
        db: Session,
        *,
        limit: int,
        offset: int,
        type_: str | None = None,
        q: str | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        query = db.query(Notification)

        if type_:
            query = query.filter(Notification.type == type_)
        if q:
            like = f"%{q.strip()}%"
            query = query.filter(
                (Notification.title.ilike(like)) | (Notification.text.ilike(like))
            )
        if user_id is not None:
            query = query.filter(Notification.user_id == user_id)
        if date_from is not None:
            query = query.filter(Notification.created_at >= date_from)
        if date_to is not None:
            query = query.filter(Notification.created_at <= date_to)

        total = query.count()
        items = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def mark_notification_read(db: Session, user_id: int, notification_id: int) -> bool:
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if not notification:
            return False

        notification.is_read = True
        db.add(notification)
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
        safe_title = (title or "").strip() or NotificationService.DEFAULT_TITLE
        safe_text = (text or "").strip()

        notification = Notification(
            user_id=user_id,
            type=type_,
            title=safe_title,
            body=safe_text,
            text=safe_text,
            url=url,
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
            created_at=NotificationService._now_utc(),
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        try:
            from app.services.telegram_bot_service import send_bot_notification_to_users

            send_bot_notification_to_users(
                db,
                user_ids=[int(user_id)],
                title=safe_title,
                text=safe_text,
                url=url,
            )
        except Exception:
            # Дублирование в Telegram не должно ломать основной сценарий сохранения уведомления.
            pass

        return notification

    @staticmethod
    def create_notifications_for_users(db: Session, payload: AdminUserTargetedNotificationIn) -> int:
        safe_title = (payload.title or "").strip() or NotificationService.DEFAULT_TITLE
        safe_text = (payload.text or "").strip()

        user_ids = sorted({int(user_id) for user_id in payload.user_ids})
        existing_ids = [u for (u,) in db.query(User.id).filter(User.id.in_(user_ids)).all()]

        objects = [
            Notification(
                user_id=user_id,
                type=payload.type,
                title=safe_title,
                body=safe_text,
                text=safe_text,
                url=payload.url,
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                is_read=False,
                created_at=NotificationService._now_utc(),
            )
            for user_id in existing_ids
        ]
        if objects:
            db.bulk_save_objects(objects)
            db.commit()
            try:
                from app.services.telegram_bot_service import send_bot_notification_to_users

                send_bot_notification_to_users(
                    db,
                    user_ids=existing_ids,
                    title=safe_title,
                    text=safe_text,
                    url=payload.url,
                )
            except Exception:
                pass

        return len(objects)

    @staticmethod
    def broadcast_notification(db: Session, payload: AdminBroadcastNotificationIn) -> int:
        safe_title = (payload.title or "").strip() or NotificationService.DEFAULT_TITLE
        safe_text = (payload.text or "").strip()

        user_ids = [u for (u,) in db.query(User.id).all()]
        objects = [
            Notification(
                user_id=user_id,
                type=payload.type,
                title=safe_title,
                body=safe_text,
                text=safe_text,
                url=payload.url,
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                is_read=False,
                created_at=NotificationService._now_utc(),
            )
            for user_id in user_ids
        ]
        if objects:
            db.bulk_save_objects(objects)
            db.commit()
            try:
                from app.services.telegram_bot_service import send_bot_notification_to_users

                send_bot_notification_to_users(
                    db,
                    user_ids=user_ids,
                    title=safe_title,
                    text=safe_text,
                    url=payload.url,
                )
            except Exception:
                pass

        return len(objects)

    @staticmethod
    def notify_training_participants(db: Session, payload: AdminCreateNotificationsForTrainingIn) -> int:
        ids = (
            db.query(Enrollment.user_id)
            .filter(
                Enrollment.training_id == payload.training_id,
                Enrollment.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.RESERVE]),
            )
            .distinct()
            .all()
        )
        user_ids = [u for (u,) in ids]

        safe_title = (payload.title or "").strip() or NotificationService.DEFAULT_TITLE
        safe_text = (payload.text or "").strip()

        objects = [
            Notification(
                user_id=user_id,
                type=payload.type,
                title=safe_title,
                body=safe_text,
                text=safe_text,
                url=payload.url,
                entity_type="training",
                entity_id=payload.training_id,
                is_read=False,
                created_at=NotificationService._now_utc(),
            )
            for user_id in user_ids
        ]
        if objects:
            db.bulk_save_objects(objects)
            db.commit()
            try:
                from app.services.telegram_bot_service import send_bot_notification_to_users

                send_bot_notification_to_users(
                    db,
                    user_ids=user_ids,
                    title=safe_title,
                    text=safe_text,
                    url=payload.url,
                )
            except Exception:
                pass

        return len(objects)
