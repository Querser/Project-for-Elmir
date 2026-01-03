from sqlalchemy import DateTime, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Setting(Base):
    __tablename__ = "settings"

    # key — PK как и раньше (это важно, чтобы ничего не сломать)
    key: Mapped[str] = mapped_column(String(150), primary_key=True)

    # id нужен для админки/индексации, но он НЕ PK
    # КРИТИЧНО: server_default, чтобы SQLAlchemy НЕ вставлял id=NULL
    # (иначе при INSERT ORM будет отправлять id=None и Postgres упадёт по NOT NULL)
    id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        server_default=text("nextval('settings_id_seq'::regclass)"),
    )

    # В БД у тебя value: text, но оставляем совместимо (и НЕ ломаем то, что работает)
    # Если хочешь идеально — можно Text, но String(255) тоже живёт (не обязательно трогать сейчас)
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
