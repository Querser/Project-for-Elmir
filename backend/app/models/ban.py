from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class BanType(str, enum.Enum):
    """
    Тип бана:
    - manual — бан, выставленный администратором вручную
    - auto   — автобан (например, за неоплату)
    """
    MANUAL = "manual"
    AUTO = "auto"


class Ban(Base):
    """
    Бан пользователя: может быть ручным или автоматическим.
    """
    __tablename__ = "bans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Причина бана (для отображения в админке)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Тип бана (manual/auto)
    type: Mapped[BanType] = mapped_column(
        Enum(BanType, name="ban_type_enum"),
        nullable=False,
        default=BanType.MANUAL,
    )

    # Активен ли бан сейчас
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Флаг, что бан был поставлен автоматически (дублирует BanType.AUTO,
    # но удобен для быстрых фильтров в коде/SQL)
    is_auto: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Когда бан был выставлен
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Когда бан был снят (если снят)
    lifted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ----- связи -----
    user: Mapped["User"] = relationship("User", back_populates="bans")

    def __repr__(self) -> str:
        return (
            f"<Ban id={self.id} user_id={self.user_id} "
            f"type={self.type} is_active={self.is_active}>"
        )
