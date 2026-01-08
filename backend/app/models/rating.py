from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .training import Training
    from .user import User


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    training_id: Mapped[int] = mapped_column(
        ForeignKey("trainings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    value: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # например 1..5
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    training: Mapped["Training"] = relationship("Training", back_populates="ratings")
    user: Mapped["User"] = relationship("User", back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("training_id", "user_id", name="uq_ratings_training_user"),
    )
