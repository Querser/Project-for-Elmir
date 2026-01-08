# app/models/price_tier.py
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .training import Training
    from .level import Level


class PriceTier(Base):
    __tablename__ = "price_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    training_id: Mapped[int] = mapped_column(
        ForeignKey("trainings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        server_default="1",
        default=1,
    )

    level_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("levels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    training: Mapped["Training"] = relationship(
        "Training",
        back_populates="price_tiers",
    )

    level: Mapped[Optional["Level"]] = relationship(
        "Level",
        back_populates="price_tiers",
    )
