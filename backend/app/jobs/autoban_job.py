from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.policies import AUTO_BAN_DELTA
from app.models.debt import Debt
from app.models.training import Training


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _debt_is_open(d: Any) -> bool:
    st = getattr(d, "status", None)
    if st is None:
        return True
    s = str(getattr(st, "value", st)).lower()
    return s in {"open", "unpaid", "created", "pending"}


def run_autoban_job(db: Session) -> dict[str, int]:
    """
    Идея: если у пользователя есть открытый долг по трене,
    и тренировка стартует <= AUTO_BAN_DELTA, ставим бан.
    """
    now = _now()
    horizon = now + AUTO_BAN_DELTA

    debts = db.query(Debt).all()
    affected = 0

    for d in debts:
        if not _debt_is_open(d):
            continue

        user_id = getattr(d, "user_id", None)
        training_id = getattr(d, "training_id", None)
        if not isinstance(user_id, int) or not isinstance(training_id, int):
            continue

        t = db.query(Training).filter(Training.id == training_id).first()
        if not t:
            continue

        start_at = getattr(t, "start_at", None)
        if not isinstance(start_at, datetime):
            continue

        if now <= start_at <= horizon:
            try:
                from app.services.ban_service import ensure_auto_debt_ban  # type: ignore
                ensure_auto_debt_ban(
                    db,
                    user_id=user_id,
                    training_id=training_id,
                    reason=f"Невыплаченный долг по тренировке #{training_id}",
                )
                affected += 1
            except Exception:
                # если ban_service не импортируется — просто пропускаем
                pass

    return {"checked": len(debts), "banned": affected}
