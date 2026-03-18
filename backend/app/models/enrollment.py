from __future__ import annotations

from datetime import datetime
import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Integer,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .training import Training


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    RESERVE = "reserve"
    CANCELLED = "cancelled"
    CANCELLED_LATE = "cancelled_late"
    NO_SHOW = "no_show"  # не пришёл


class Enrollment(Base):
    """
    Запись пользователя на тренировку (основа или резерв).
    """
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "training_id", name="uq_enrollment_user_training"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    training_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trainings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # False = основа, True = резерв
    is_reserve: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus, name="enrollmentstatus"),
        nullable=False,
        default=EnrollmentStatus.ACTIVE,
    )

    # факт оплаты (пока просто флажок, дальше увяжем с платежами)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    position_key: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    user: Mapped["User"] = relationship("User", back_populates="enrollments")
    training: Mapped["Training"] = relationship("Training", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<Enrollment id={self.id} user_id={self.user_id} training_id={self.training_id}>"
