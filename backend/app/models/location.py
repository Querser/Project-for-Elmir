from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .training import Training


class Location(Base):
    __tablename__ = "locations"

    # ВАЖНО: мы маппим только id — это гарантированно есть в таблице.
    # Остальные колонки (какие бы они ни были) SQLAlchemy не обязаны знать,
    # и это не будет ломать запросы trainings.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    trainings: Mapped[list["Training"]] = relationship(
        "Training",
        back_populates="location",
        lazy="selectin",
        foreign_keys="Training.location_id",
    )

    def __repr__(self) -> str:
        return f"<Location id={self.id}>"
