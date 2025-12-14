# app/models/audit_log.py
from datetime import datetime

from sqlalchemy import Integer, DateTime, String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AuditLog(Base):
    """
    Журнал действий (лог).
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    object_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    meta: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Дополнительные данные в JSON-формате (строка)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    user: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r}>"
