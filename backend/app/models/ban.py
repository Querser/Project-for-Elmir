# backend/app/models/ban.py
from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

from .base import Base


class BanType(str, enum.Enum):
    # В БД enum public.bantype = ('MANUAL', 'AUTO_DEBT')
    MANUAL = "MANUAL"
    AUTO_DEBT = "AUTO_DEBT"


BAN_TYPE_ENUM = PGEnum(
    BanType.MANUAL.value,
    BanType.AUTO_DEBT.value,
    name="bantype",
    schema="public",
    create_type=False,
)


class Ban(Base):
    __tablename__ = "bans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # колонка в БД называется "type"
    type: Mapped[str] = mapped_column(BAN_TYPE_ENUM, nullable=False)

    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # если в User есть relationship(... back_populates="user"), это нужно
    user: Mapped["User"] = relationship("User", back_populates="bans")

    def __repr__(self) -> str:
        return f"<Ban id={self.id} user_id={self.user_id} type={self.type} active={self.active}>"
