# app/models/ban.py
from datetime import datetime
import enum

from sqlalchemy import Integer, DateTime, String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class BanType(str, enum.Enum):
    MANUAL = "manual"
    AUTO_DEBT = "auto_debt"


class Ban(Base):
    """
    Бан/автобан пользователя (в т.ч. за долги).
    """
    __tablename__ = "bans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    type: Mapped[BanType] = mapped_column(Enum(BanType), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="bans")

    def __repr__(self) -> str:
        return f"<Ban id={self.id} user_id={self.user_id} type={self.type}>"
