from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Any

from sqlalchemy.orm import Session

from app.models.debt import Debt, DebtStatus


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def has_open_debts(db: Session, user_id: int) -> bool:
    """
    True если у пользователя есть хотя бы один OPEN-долг.
    Это имя ожидает enrollment_service.py
    """
    return (
        db.query(Debt.id)
        .filter(Debt.user_id == user_id, Debt.status == DebtStatus.OPEN)
        .first()
        is not None
    )


# ---- Backward-compatible aliases (на случай старых импортов) ----
user_has_open_debts = has_open_debts
has_debts = has_open_debts


def list_debts(
    db: Session,
    *,
    user_id: Optional[int] = None,
    training_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Debt]:
    q = db.query(Debt)
    if user_id is not None:
        q = q.filter(Debt.user_id == user_id)
    if training_id is not None:
        q = q.filter(Debt.training_id == training_id)
    if status is not None:
        # status может прилететь строкой из API
        try:
            status_enum = DebtStatus(status)
            q = q.filter(Debt.status == status_enum)
        except Exception:
            q = q.filter(Debt.status == status)
    return q.order_by(Debt.id.desc()).offset(offset).limit(limit).all()


def get_debt(db: Session, debt_id: int) -> Optional[Debt]:
    return db.query(Debt).filter(Debt.id == debt_id).first()


get_debt_by_id = get_debt  # alias


def get_open_debt_for_training(db: Session, *, user_id: int, training_id: int) -> Optional[Debt]:
    return (
        db.query(Debt)
        .filter(
            Debt.user_id == user_id,
            Debt.training_id == training_id,
            Debt.status == DebtStatus.OPEN,
        )
        .order_by(Debt.id.desc())
        .first()
    )


def create_debt_for_training(
    db: Session,
    *,
    user_id: int,
    training_id: int,
    amount: Decimal,
) -> Debt:
    """
    Идемпотентно: если уже есть OPEN-долг по этой тренировке  возвращаем его.
    """
    existing = get_open_debt_for_training(db, user_id=user_id, training_id=training_id)
    if existing is not None:
        return existing

    debt = Debt(
        user_id=user_id,
        training_id=training_id,
        amount=amount,
        status=DebtStatus.OPEN,
        created_at=_now_utc(),
        closed_at=None,
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt


# aliases на случай старых импортов/роутов
ensure_debt_for_training = create_debt_for_training
create_debt = create_debt_for_training


def close_debt_for_training(db: Session, *, user_id: int, training_id: int) -> int:
    """
    Закрывает OPEN-долги по тренировке.
    Возвращает количество закрытых.
    """
    now = _now_utc()
    debts = (
        db.query(Debt)
        .filter(
            Debt.user_id == user_id,
            Debt.training_id == training_id,
            Debt.status == DebtStatus.OPEN,
        )
        .all()
    )

    for d in debts:
        d.status = DebtStatus.CLOSED
        d.closed_at = now

    if debts:
        db.commit()

        # если был автобан за долг  снимаем
        try:
            from app.services.ban_service import deactivate_auto_debt_bans_if_any
            deactivate_auto_debt_bans_if_any(db, user_id=user_id)
        except Exception:
            # не роняем закрытие долга из-за проблем в бан-сервисе
            pass

    return len(debts)


close_debt_by_training = close_debt_for_training  # alias


def close_debt(db: Session, *args: Any, **kwargs: Any) -> int:
    """
    ВАЖНО: это имя ожидает admin_billing.py (from debt_service import close_debt).

    Поддерживает варианты вызова:
      - close_debt(db, debt_id)
      - close_debt(db, user_id, training_id)
      - close_debt(db, debt_id=<id>)
      - close_debt(db, user_id=<id>, training_id=<id>)
    Возвращает кол-во закрытых долгов (0/1/..).
    """
    debt_id = kwargs.get("debt_id")
    user_id = kwargs.get("user_id")
    training_id = kwargs.get("training_id")

    if debt_id is None and len(args) == 1:
        debt_id = args[0]
    elif (user_id is None or training_id is None) and len(args) == 2:
        user_id, training_id = args[0], args[1]

    if debt_id is not None:
        d = get_debt(db, int(debt_id))
        if d is None:
            return 0
        # Закрываем по связке user_id+training_id (на случай дублей)
        return close_debt_for_training(db, user_id=d.user_id, training_id=d.training_id)

    if user_id is not None and training_id is not None:
        return close_debt_for_training(db, user_id=int(user_id), training_id=int(training_id))

    raise TypeError("close_debt(): expected debt_id OR (user_id, training_id)")
