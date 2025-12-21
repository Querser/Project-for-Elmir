# backend/app/services/debt_service.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.debt import Debt
from app.models.training import Training
from app.services.ban_service import deactivate_auto_debt_bans_if_any


def has_open_debts(db: Session, *, user_id: int) -> bool:
    return (
        db.query(Debt)
        .filter(
            Debt.user_id == user_id,
            Debt.status == "OPEN",
        )
        .first()
        is not None
    )


def create_open_debt_if_missing(db: Session, *, user_id: int, training: Training) -> Debt:
    existing = (
        db.query(Debt)
        .filter(
            Debt.user_id == user_id,
            Debt.training_id == training.id,
            Debt.status == "OPEN",
        )
        .first()
    )
    if existing:
        return existing

    debt = Debt(
        user_id=user_id,
        training_id=training.id,
        amount=Decimal(str(training.price)),
        status="OPEN",
        closed_at=None,
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt


def close_debt_for_training(db: Session, *, user_id: int, training_id: int) -> None:
    debt = (
        db.query(Debt)
        .filter(
            Debt.user_id == user_id,
            Debt.training_id == training_id,
            Debt.status == "OPEN",
        )
        .first()
    )
    if not debt:
        raise AppException(error_code="NOT_FOUND", message="Открытый долг не найден")

    debt.status = "CLOSED"
    debt.closed_at = datetime.utcnow()
    db.commit()

    # Если открытых долгов больше нет — снимаем автобан
    if not has_open_debts(db, user_id=user_id):
        deactivate_auto_debt_bans_if_any(db, user_id=user_id)
