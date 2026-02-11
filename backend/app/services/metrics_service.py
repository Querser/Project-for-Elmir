from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.models.payment import Payment, PaymentStatus


class MetricsService:
    _lock = Lock()
    _requests_total = 0
    _http_4xx_total = 0
    _http_5xx_total = 0
    _exceptions_total = 0

    @classmethod
    def record_http_status(cls, status_code: int) -> None:
        with cls._lock:
            cls._requests_total += 1
            if 400 <= int(status_code) < 500:
                cls._http_4xx_total += 1
            if int(status_code) >= 500:
                cls._http_5xx_total += 1

    @classmethod
    def record_exception(cls) -> None:
        with cls._lock:
            cls._exceptions_total += 1

    @classmethod
    def snapshot(cls, db: Session) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        enrollments_today = int(
            db.query(func.count(Enrollment.id))
            .filter(Enrollment.created_at >= start_of_day)
            .scalar()
            or 0
        )
        payments_created_today = int(
            db.query(func.count(Payment.id))
            .filter(Payment.created_at >= start_of_day)
            .scalar()
            or 0
        )
        payments_paid_today = int(
            db.query(func.count(Payment.id))
            .filter(
                Payment.paid_at.isnot(None),
                Payment.paid_at >= start_of_day,
                Payment.status == PaymentStatus.PAID,
            )
            .scalar()
            or 0
        )

        with cls._lock:
            return {
                "timestamp_utc": now.isoformat(),
                "requests_total": cls._requests_total,
                "http_4xx_total": cls._http_4xx_total,
                "http_5xx_total": cls._http_5xx_total,
                "exceptions_total": cls._exceptions_total,
                "enrollments_today": enrollments_today,
                "payments_created_today": payments_created_today,
                "payments_paid_today": payments_paid_today,
            }

