from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.setting import Setting


DEFAULT_SETTINGS: dict[str, tuple[str, str]] = {
    # key: (value, description)
    "cancel_hours_before_training": ("4", "Запрет отмены записи менее чем за N часов до начала"),
    "autoban_hours_before_training": ("2", "Автобан/долг за неоплату за N часов до начала"),
    "ban_text_default": ("У вас бан. Обратитесь к администратору.", "Текст по умолчанию для экрана бана"),
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

    # удобные typed-getters (на будущее, чтобы код тренировок/банов мог читать настройки)
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
