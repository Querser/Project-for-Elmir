# app/services/user_service.py
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.user import UserProfileUpdate


# --------- Нормализация телефона --------- #
def normalize_phone(raw_phone: str) -> str:
    """
    Простая нормализация под российский номер:
    - оставляем только цифры;
    - допускаем 10 или 11 цифр;
    - приводим к формату +7XXXXXXXXXX.
    """
    if not raw_phone:
        raise AppException(
            error_code="BAD_REQUEST",
            message="Телефон не может быть пустым",
        )

    digits = "".join(ch for ch in raw_phone if ch.isdigit())

    # Примеры:
    # 8 999 123-45-67  -> 89991234567
    # +7 (999) 1234567 -> 79991234567
    if len(digits) == 11 and digits[0] in ("7", "8"):
        digits = digits[1:]
    elif len(digits) == 10:
        pass
    else:
        raise AppException(
            error_code="BAD_REQUEST",
            message="Некорректный формат телефона",
        )

    return "+7" + digits


# --------- Создание/обновление пользователя из Telegram --------- #
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
    Создаёт или обновляет пользователя по данным из Telegram.
    Вызывается из middleware после успешной валидации initData.
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

    if user is None:
        # новый пользователь – заполняем всё, что пришло из Telegram
        user = User(
            telegram_id=telegram_id_int,
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone=normalized_phone,
            is_active=True,
        )
        db.add(user)
    else:
        # существующий пользователь:
        # НЕ перезатираем вручную изменённый профиль данными из Telegram
        if username is not None and not user.username:
            user.username = username or user.username

        if first_name is not None and not user.first_name:
            user.first_name = first_name or user.first_name

        if last_name is not None and not user.last_name:
            user.last_name = last_name or user.last_name

        # телефон из Telegram используем только если у пользователя ещё нет телефона
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

    db.commit()
    db.refresh(user)
    return user


# --------- Обновление профиля пользователя через API --------- #
def update_user_profile(
    db: Session,
    user: User,
    data: UserProfileUpdate,
) -> User:
    """
    Обновляет профиль (имя, телефон, пол, дата рождения, уровень и т.п.).
    ВАЖНО: current_user приходит из другой сессии (из middleware),
    поэтому сначала "прикрепляем" его к текущей сессии через merge().
    """

    # Гарантируем, что объект user прикреплён к сессии db
    user = db.merge(user)

    # Имя / фамилия / username
    if data.first_name is not None:
        user.first_name = data.first_name.strip() or None

    if data.last_name is not None:
        user.last_name = data.last_name.strip() or None

    if data.username is not None:
        user.username = data.username.strip() or None

    # Телефон
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
            raise AppException(
                error_code="BAD_REQUEST",
                message="Этот телефон уже используется другим пользователем",
            )

        user.phone = normalized_phone

    # Пол
    if data.gender is not None:
        user.gender = data.gender

    # Дата рождения
    if data.birth_date is not None:
        user.birth_date = data.birth_date

    # Уровень
    if data.level_id is not None:
        user.level_id = data.level_id

    # Флаг видимости Telegram
    if data.is_telegram_public is not None:
        user.is_telegram_public = data.is_telegram_public

    db.commit()
    db.refresh(user)
    return user
