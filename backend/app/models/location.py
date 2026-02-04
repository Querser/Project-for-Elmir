from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .training import Training


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # новые поля (можно nullable=True — безопасно)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # для карты
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    trainings: Mapped[list["Training"]] = relationship(
        "Training",
        back_populates="location",
        lazy="selectin",
        foreign_keys="Training.location_id",
    )

    def __repr__(self) -> str:
        return f"<Location id={self.id} name={self.name!r}>"