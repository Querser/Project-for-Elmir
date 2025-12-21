# backend/app/models/debt.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, DateTime, ForeignKey, Numeric, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

from .base import Base


# В БД enum public.debtstatus = ('OPEN', 'CLOSED')
DEBT_STATUS_ENUM = PGEnum(
    "OPEN",
    "CLOSED",
    name="debtstatus",
    schema="public",
    create_type=False,
)


class Debt(Base):
    __tablename__ = "debts"
    __table_args__ = (UniqueConstraint("user_id", "training_id", name="uq_debt_user_training"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    training_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trainings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("0"),
    )

    status: Mapped[str] = mapped_column(
        DEBT_STATUS_ENUM,
        nullable=False,
        server_default=text("'OPEN'::public.debtstatus"),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User")
    training: Mapped["Training"] = relationship("Training")

    def __repr__(self) -> str:
        return f"<Debt id={self.id} user_id={self.user_id} training_id={self.training_id} status={self.status}>"
