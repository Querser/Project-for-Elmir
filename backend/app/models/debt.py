from __future__ import annotations

import enum
from typing import Optional
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, func, text
from sqlalchemy.orm import relationship

from app.db.base import Base


class DebtStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Debt(Base):
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False, index=True)

    amount = Column(Numeric(12, 2), nullable=False)

    # В Postgres enum называется debtstatus (у тебя он уже создан миграцией)
    status = Column(SAEnum(DebtStatus, name="debtstatus"), nullable=False, server_default=text("'OPEN'"))

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", lazy="selectin")
    training = relationship("Training", lazy="selectin")
