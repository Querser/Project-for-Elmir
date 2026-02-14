from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.user import UserProfileUpdate
from app.services.level_service import get_default_level_id


def normalize_phone(raw_phone: str) -> str:
    """
    Normalize Russian phone numbers to +7XXXXXXXXXX.
    """
    if raw_phone is None:
        raise AppException(message="Телефон не может быть пустым. Пример: +7 (999) 123-45-67")

    raw_phone = str(raw_phone).strip()
    if not raw_phone:
        raise AppException(message="Телефон не может быть пустым. Пример: +7 (999) 123-45-67")

    digits = "".join(ch for ch in raw_phone if ch.isdigit())

    if len(digits) == 11 and digits[0] in ("7", "8"):
        digits = digits[1:]
    elif len(digits) == 10:
        pass
    else:
        raise AppException(
            message=(
                "Некорректный формат телефона. "
                "Введите российский номер на 10 цифр (без +7/8) или на 11 цифр (с 7/8). "
                "Пример: +7 (999) 123-45-67 или 8 999 123-45-67."
            )
        )

    if len(digits) != 10:
        raise AppException(
            message=(
                "Некорректный формат телефона. "
                "Пример: +7 (999) 123-45-67 или 8 999 123-45-67."
            )
        )

    return "+7" + digits


def get_or_create_user_from_telegram(
    db: Session,
    *,
    telegram_id: int | str,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    phone: Optional[str] = None,
) -> User:
    """
    Create/update user from Telegram payload.
    """
    telegram_id_int = int(telegram_id)

    user = (
        db.query(User)
        .filter(User.telegram_id == telegram_id_int)
        .one_or_none()
    )

    normalized_phone: Optional[str] = None
    if phone:
        normalized_phone = normalize_phone(phone)

    default_level_id = get_default_level_id(db)

    if user is None:
        user = User(
            telegram_id=telegram_id_int,
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone=normalized_phone,
            level_id=default_level_id,
            is_active=True,
        )
        db.add(user)
    else:
        if username is not None and not user.username:
            user.username = username or user.username

        if first_name is not None and not user.first_name:
            user.first_name = first_name or user.first_name

        if last_name is not None and not user.last_name:
            user.last_name = last_name or user.last_name

        if normalized_phone and not user.phone:
            other = (
                db.query(User)
                .filter(
                    User.phone == normalized_phone,
                    User.id != user.id,
                )
                .one_or_none()
            )
            if not other:
                user.phone = normalized_phone

        # Backfill old accounts without level.
        if user.level_id is None and default_level_id is not None:
            user.level_id = default_level_id

    db.commit()
    db.refresh(user)
    return user


def update_user_profile(
    db: Session,
    user: User,
    data: UserProfileUpdate,
) -> User:
    """
    Update profile fields from API payload.
    """
    user = db.merge(user)

    if data.first_name is not None:
        user.first_name = data.first_name.strip() or None

    if data.last_name is not None:
        user.last_name = data.last_name.strip() or None

    if data.username is not None:
        user.username = data.username.strip() or None

    if data.phone is not None:
        normalized_phone = normalize_phone(data.phone)

        other = (
            db.query(User)
            .filter(
                User.phone == normalized_phone,
                User.id != user.id,
            )
            .one_or_none()
        )
        if other:
            raise AppException(message="Этот телефон уже используется другим пользователем")

        user.phone = normalized_phone

    if data.gender is not None:
        user.gender = data.gender

    if data.birth_date is not None:
        user.birth_date = data.birth_date

    if data.level_id is not None:
        user.level_id = data.level_id

    if data.is_telegram_public is not None:
        user.is_telegram_public = data.is_telegram_public

    db.commit()
    db.refresh(user)
    return user
