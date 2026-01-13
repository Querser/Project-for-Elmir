from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .training import Training
    from .user import User


class Rating(Base):
    """
    Оценка тренировки пользователем.
    Нужны BOTH FK:
      - user_id -> users.id
      - training_id -> trainings.id
    Иначе relationship Training.ratings не сможет собрать join condition.
    """
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # ✅ ВАЖНО: это поле нужно для Training.ratings
    training_id: Mapped[int] = mapped_column(
        ForeignKey("trainings.id"),
        nullable=False,
        index=True,
    )

    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="ratings")
    training: Mapped["Training"] = relationship("Training", back_populates="ratings")
