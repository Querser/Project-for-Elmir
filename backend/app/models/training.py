# app/models/training.py
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Training(Base):
    """
    Конкретная тренировка в расписании.
    """
    __tablename__ = "trainings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=90)

    min_level_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_level_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    capacity_main: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    capacity_reserve: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    coach_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    location_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    location: Mapped["Location | None"] = relationship("Location", back_populates="trainings")

    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="training",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="training",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Training id={self.id} title={self.title!r}>"
