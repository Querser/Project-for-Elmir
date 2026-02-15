from __future__ import annotations

import calendar
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.payment import Payment

RETENTION_MONTHS = 3


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _subtract_months(dt: datetime, months: int) -> datetime:
    year = dt.year
    month = dt.month - months
    while month <= 0:
        month += 12
        year -= 1

    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def quarter_cutoff(now: datetime | None = None) -> datetime:
    base = _ensure_utc(now or datetime.now(timezone.utc))
    return _subtract_months(base, RETENTION_MONTHS)


def purge_payments_older_than_quarter(db: Session, *, now: datetime | None = None) -> int:
    cutoff = quarter_cutoff(now)
    deleted = (
        db.query(Payment)
        .filter(Payment.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    return int(deleted or 0)
