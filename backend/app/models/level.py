# app/models/level.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .price_tier import PriceTier


class Level(Base):
    """
    Уровень игрока: Новичок, Средний-, Средний, Средний+.
    """
    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    users: Mapped[list["User"]] = relationship("User", back_populates="level")

    # ВАЖНО: обратная связь для PriceTier.level (back_populates="level")
    price_tiers: Mapped[list["PriceTier"]] = relationship(
        "PriceTier",
        back_populates="level",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Level id={self.id} name={self.name!r}>"
