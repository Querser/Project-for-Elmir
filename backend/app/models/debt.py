# app/models/debt.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base  # ВАЖНО: берём Base из models/base.py


class Debt(Base):
    """
    Долг пользователя за тренировку.
    """
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    training_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("trainings.id", ondelete="SET NULL"),
        nullable=True,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="debts")
    training: Mapped["Training | None"] = relationship("Training")

    def __repr__(self) -> str:
        return f"<Debt id={self.id} user_id={self.user_id} amount={self.amount}>"
