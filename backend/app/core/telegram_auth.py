# app/core/telegram_auth.py

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from hmac import new as hmac_new
from typing import Any, Dict, Optional
from urllib.parse import unquote

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models import User

logger = logging.getLogger("app.telegram")


@dataclass
class TelegramInitData:
    raw: str
    data: Dict[str, str]
    user: Optional[Dict[str, Any]]
    auth_date: Optional[int]


class TelegramAuthError(AppException):
    """Исключение при ошибках валидации Telegram initData."""

    def __init__(self, message: str = "Невалидные данные авторизации Telegram") -> None:
        super().__init__(
            error_code="TELEGRAM_AUTH_ERROR",
            message=message,
            status_code=401,
        )


def parse_and_validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 24 * 60 * 60,
) -> TelegramInitData:
    """
    Валидирует initData, полученный из Telegram.WebApp.initData.

    Алгоритм:
    - парсим query-строку key=value&key2=value2...
    - отделяем hash;
    - по остальным key=value строим data_check_string (сортировка по ключу, разделитель '\n');
    - считаем секретный ключ: HMAC_SHA256("WebAppData", bot_token);
    - считаем подпись HMAC_SHA256(data_check_string, secret_key) и сравниваем с hash.
    """

    if not init_data:
        raise TelegramAuthError("Пустые данные авторизации Telegram")

    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в окружении")

    hash_value = ""
    data_dict: Dict[str, str] = {}

    # initData — строка вида key=value&key2=value2...
    for chunk in init_data.split("&"):
        if not chunk:
            continue
        try:
            key, value = chunk.split("=", 1)
        except ValueError:
            # странный кусок, пропускаем
            continue

        if key == "hash":
            hash_value = value
            continue

        data_dict[key] = unquote(value)

    if not hash_value:
        raise TelegramAuthError("В initData отсутствует параметр hash")

    # Строка для подписи
    data_check_string = "\n".join(
        f"{key}={data_dict[key]}" for key in sorted(data_dict.keys())
    )

    # Считаем секретный ключ и подпись
    secret_key = hmac_new(
        "WebAppData".encode("utf-8"),
        bot_token.encode("utf-8"),
        sha256,
    ).digest()
    data_check = hmac_new(
        secret_key,
        data_check_string.encode("utf-8"),
        sha256,
    ).hexdigest()

    if data_check != hash_value:
        raise TelegramAuthError("Подпись Telegram недействительна")

    # Контроль срока действия auth_date
    auth_ts: Optional[int] = None
    if "auth_date" in data_dict:
        try:
            auth_ts = int(data_dict["auth_date"])
            if max_age_seconds > 0:
                now_ts = int(datetime.now(tz=timezone.utc).timestamp())
                if now_ts - auth_ts > max_age_seconds:
                    raise TelegramAuthError("Сессия Telegram истекла")
        except ValueError:
            logger.warning("Не удалось распарсить auth_date: %s", data_dict["auth_date"])

    user_dict: Optional[Dict[str, Any]] = None
    if "user" in data_dict:
        try:
            user_dict = json.loads(data_dict["user"])
        except json.JSONDecodeError:
            logger.warning("Не удалось распарсить поле user из initData")

    return TelegramInitData(raw=init_data, data=data_dict, user=user_dict, auth_date=auth_ts)


def get_or_create_user(db: Session, tg_init: TelegramInitData) -> User:
    """
    Создаёт или обновляет запись пользователя в БД по данным из Telegram.
    """
    if not tg_init.user or "id" not in tg_init.user:
        raise TelegramAuthError("В initData отсутствует информация о пользователе")

    tg_user = tg_init.user
    telegram_id = int(tg_user["id"])
    username = tg_user.get("username")
    first_name = tg_user.get("first_name")
    last_name = tg_user.get("last_name")

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
        )
        db.add(user)
        db.flush()
        logger.info("Создан новый пользователь Telegram id=%s db_id=%s", telegram_id, user.id)
    else:
        changed = False
        if username and user.username != username:
            user.username = username
            changed = True
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            changed = True
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            changed = True

        if changed:
            logger.info("Обновлены данные пользователя Telegram id=%s db_id=%s", telegram_id, user.id)

    return user
