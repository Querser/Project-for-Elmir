from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.setting import Setting


DEFAULT_SETTINGS: dict[str, tuple[str, str]] = {
    "cancel_hours_before_training": ("4", "Hours before training when cancellation is forbidden"),
    "autoban_hours_before_training": ("2", "Hours before training for autoban on unpaid enrollment"),
    "ban_text_default": ("У вас бан. Обратитесь к администратору.", "Default text for banned users"),
    "contacts_text": (
        "Контакты администратора:\nТелефон: +7 (000) 000-00-00\nTelegram: @elmiravolley",
        "Text for Telegram bot Contacts button",
    ),
    "rules_text": (
        "Правила школы:\n1) Приходите заранее.\n2) Учитывайте срок отмены.\n3) Соблюдайте уважительное общение.",
        "Text for Telegram bot Rules button",
    ),
}


class SettingsService:
    @staticmethod
    def list(db: Session) -> list[Setting]:
        return db.query(Setting).order_by(Setting.key.asc()).all()

    @staticmethod
    def get(db: Session, key: str) -> Optional[Setting]:
        return db.query(Setting).filter(Setting.key == key).one_or_none()

    @staticmethod
    def upsert(db: Session, key: str, value: str, description: Optional[str] = None) -> Setting:
        row = SettingsService.get(db, key)
        if row is None:
            row = Setting(key=key, value=value, description=description)
            db.add(row)
        else:
            row.value = value
            if description is not None:
                row.description = description

        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete(db: Session, key: str) -> bool:
        row = SettingsService.get(db, key)
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True

    @staticmethod
    def seed_defaults(db: Session) -> int:
        created = 0
        for key, (value, desc) in DEFAULT_SETTINGS.items():
            if SettingsService.get(db, key) is None:
                db.add(Setting(key=key, value=value, description=desc))
                created += 1
        if created:
            db.commit()
        return created

    @staticmethod
    def get_int(db: Session, key: str, default: int) -> int:
        row = SettingsService.get(db, key)
        if row is None:
            return default
        try:
            return int(row.value)
        except Exception:
            return default

    @staticmethod
    def get_str(db: Session, key: str, default: str) -> str:
        row = SettingsService.get(db, key)
        return row.value if row else default

