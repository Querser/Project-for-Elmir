from __future__ import annotations

from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .audit_log import AuditLog
    from .ban import Ban
    from .debt import Debt
    from .enrollment import Enrollment
    from .level import Level
    from .notification import Notification
    from .payment import Payment
    from .rating import Rating


class User(Base):
    """Пользователь / игрок волейбольной школы."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Telegram
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
        index=True,
    )
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Имя / фамилия
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Контактные данные
    phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        unique=True,
        index=True,
    )

    # Уровень игрока
    level_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("levels.id"),
        nullable=True,
    )

    # Статистика
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    cups: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    # Профиль
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Флаг видимости Telegram в профиле
    is_telegram_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="1",
    )

    # Поля для интеграции оплат
    payer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    card_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)

    # Флаги
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="1",
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
    )

    # Служебные поля
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # -------- связи --------
    level: Mapped[Optional["Level"]] = relationship(
        "Level",
        back_populates="users",
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="user",
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="user",
    )

    debts: Mapped[list["Debt"]] = relationship(
        "Debt",
        back_populates="user",
    )

    bans: Mapped[list["Ban"]] = relationship(
        "Ban",
        back_populates="user",
    )

    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
    )

    # ✅ РЕЙТИНГИ (оценки тренировок пользователем)
    ratings: Mapped[list["Rating"]] = relationship(
        "Rating",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} tg_id={self.telegram_id}>"
