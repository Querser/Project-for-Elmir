from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import case, literal

from .base import Base

if TYPE_CHECKING:
    from .enrollment import Enrollment
    from .payment import Payment
    from .price_tier import PriceTier
    from .rating import Rating
    from .location import Location


class Training(Base):
    __tablename__ = "trainings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # По твоему \d trainings:
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Основное поле времени старта (новое)
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    min_level_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    max_level_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    capacity_main: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_reserve: Mapped[int] = mapped_column(Integer, nullable=False)

    coach_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_cancelled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    # ---------------- Алиасы для совместимости ----------------
    # Старый контракт/схемы часто ждут starts_at / ends_at.
    # Делаем так, чтобы from_orm / сериализация брали значения, а старый код мог читать/писать.

    @hybrid_property
    def starts_at(self) -> datetime:
        return self.start_at

    @starts_at.setter
    def starts_at(self, value: datetime) -> None:
        self.start_at = value

    @starts_at.expression
    def starts_at(cls):
        return cls.start_at

    @property
    def end_at(self) -> Optional[datetime]:
        # В БД нет end_at — считаем из duration_minutes
        if self.start_at is None or self.duration_minutes is None:
            return None
        return self.start_at + timedelta(minutes=int(self.duration_minutes))

    @property
    def ends_at(self) -> Optional[datetime]:
        # Алиас под старый контракт
        return self.end_at

    @ends_at.setter
    def ends_at(self, value: Optional[datetime]) -> None:
        """
        Если старый код пытается выставить ends_at, пересчитываем duration_minutes.
        Если start_at ещё не задан — ничего не делаем (безопасно).
        """
        if value is None:
            return
        if self.start_at is None:
            return
        delta = value - self.start_at
        minutes = int(delta.total_seconds() // 60)
        # duration_minutes у нас NOT NULL, но setter вызывается только если реально задают ends_at
        self.duration_minutes = max(0, minutes)

    # Доп. алиасы (иногда фронт/клиент ожидает camelCase)
    @property
    def startsAt(self) -> datetime:
        return self.start_at

    @property
    def endsAt(self) -> Optional[datetime]:
        return self.end_at

    # --------- совместимость со старым кодом (status) ----------
    @hybrid_property
    def status(self) -> str:
        return "cancelled" if self.is_cancelled else "scheduled"

    @status.expression
    def status(cls):
        return case(
            (cls.is_cancelled.is_(True), literal("cancelled")),
            else_=literal("scheduled"),
        )

    # -------- relationships --------
    location: Mapped[Optional["Location"]] = relationship(
        "Location",
        back_populates="trainings",
        lazy="selectin",
        foreign_keys="Training.location_id",
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="training",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="training",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    price_tiers: Mapped[list["PriceTier"]] = relationship(
        "PriceTier",
        back_populates="training",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    ratings: Mapped[list["Rating"]] = relationship(
        "Rating",
        back_populates="training",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Training id={self.id} title={self.title!r} start_at={self.start_at}>"