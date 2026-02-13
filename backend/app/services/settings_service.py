from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.setting import Setting


DEFAULT_BAN_TEXT = "У вас бан. Обратитесь к администратору."
DEFAULT_CONTACTS_TEXT = (
    "Контакты администратора:\n"
    "Телефон: +7 (000) 000-00-00\n"
    "Telegram: @elmiravolley"
)
DEFAULT_RULES_TEXT = (
    "Правила школы:\n"
    "1) Приходите заранее.\n"
    "2) Учитывайте срок отмены.\n"
    "3) Соблюдайте уважительное общение."
)
DEFAULT_PROMOTIONS_TEXT = (
    "Актуальные акции и предложения:\n"
    "1) Скидка на первое посещение.\n"
    "2) Бонусы за регулярные тренировки.\n"
    "3) Специальные условия на абонементы."
)


DEFAULT_SETTINGS: dict[str, tuple[str, str]] = {
    "cancel_hours_before_training": ("4", "Hours before training when cancellation is forbidden"),
    "autoban_hours_before_training": ("2", "Hours before training for autoban on unpaid enrollment"),
    "ban_text_default": (DEFAULT_BAN_TEXT, "Default text for banned users"),
    "contacts_text": (DEFAULT_CONTACTS_TEXT, "Shared text for Contacts section (bot + miniapp)"),
    "rules_text": (DEFAULT_RULES_TEXT, "Shared text for Rules section (bot + miniapp)"),
    "promotions_text": (DEFAULT_PROMOTIONS_TEXT, "Shared text for Promotions section (bot + miniapp)"),
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
