# backend/app/jobs/autoban_job.py
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.training import Training
from app.services.debt_service import create_open_debt_if_missing
from app.services.ban_service import ensure_auto_debt_ban


# По ТЗ “N часов до начала”. Глобальные настройки будут в этапе 11,
# пока держим константой (можешь поставить 1 или 2).
AUTO_BAN_HOURS_BEFORE_TRAINING = 2


def run_autoban_job(db: Session) -> int:
    now = datetime.utcnow()
    border = now + timedelta(hours=AUTO_BAN_HOURS_BEFORE_TRAINING)

    rows = (
        db.query(Enrollment, Training)
        .join(Training, Training.id == Enrollment.training_id)
        .filter(
            Enrollment.status == EnrollmentStatus.ACTIVE,
            Enrollment.is_paid.is_(False),
            Training.is_cancelled.is_(False),
            Training.start_at > now,
            Training.start_at <= border,
        )
        .all()
    )

    processed = 0
    for enrollment, training in rows:
        debt = create_open_debt_if_missing(db, user_id=enrollment.user_id, training=training)

        reason = f"Неоплата тренировки #{training.id} (долг #{debt.id}, сумма {float(training.price):.2f})"
        ensure_auto_debt_ban(db, user_id=enrollment.user_id, reason=reason)

        processed += 1

    return processed


if __name__ == "__main__":
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        count = run_autoban_job(db)
        print(f"autoban_job: processed={count}")
    finally:
        db.close()
