from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import relationship

from app.db.base import Base


class BanType(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTO_DEBT = "AUTO_DEBT"


class Ban(Base):
    __tablename__ = "bans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # В Postgres enum называется bantype (у тебя он уже создан миграцией)
    type = Column(SAEnum(BanType, name="bantype"), nullable=False)

    reason = Column(String, nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    until = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", lazy="selectin")

    def is_active(self, now: Optional[datetime] = None) -> bool:
        if not self.active:
            return False
        if self.until is None:
            return True

        now = now or datetime.utcnow()
        # На всякий случай: сравнение naive/aware
        try:
            return now <= self.until
        except TypeError:
            return now.replace(tzinfo=None) <= self.until.replace(tzinfo=None)
