# backend/app/core/telegram_auth.py
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from hmac import new as hmac_new
from typing import Any, Dict, Optional
from urllib.parse import unquote

from app.core.exceptions import AppException

logger = logging.getLogger("app.telegram")


@dataclass
class TelegramInitData:
    """
    Разобранные и провалидированные данные initData.
    """
    raw: str                   # исходная строка
    data: Dict[str, str]       # все пары key -> value (уже unquote)
    user: Optional[Dict[str, Any]]  # JSON user из Telegram, если есть
    auth_date: Optional[int]   # timestamp auth_date, если есть


class TelegramAuthError(AppException):
    """
    Ошибка валидации Telegram initData.
    """

    def __init__(self, message: str = "Невалидные данные авторизации Telegram") -> None:
        super().__init__(
            error_code="TELEGRAM_AUTH_ERROR",
            message=message,
            status_code=401,
        )


def _build_data_check_string(data: Dict[str, str]) -> str:
    """
    Строка для подписи: key=value по всем ключам, отсортированным по алфавиту.
    """
    return "\n".join(f"{key}={data[key]}" for key in sorted(data.keys()))


def _compute_hash(data: Dict[str, str], bot_token: str) -> str:
    """
    Вычисляем hash так же, как описано в документации Telegram Web Apps.

    Эту же функцию используем в tools/generate_init_data.py.
    """
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

    data_check_string = _build_data_check_string(data)

    # секретный ключ HMAC
    secret_key = hmac_new(
        "WebAppData".encode("utf-8"),
        bot_token.encode("utf-8"),
        sha256,
    ).digest()

    # финальный hash
    return hmac_new(
        secret_key,
        data_check_string.encode("utf-8"),
        sha256,
    ).hexdigest()


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 24 * 60 * 60,
) -> TelegramInitData:
    """
    Разбор и валидация initData из Telegram.WebApp.initData.

    Возвращает TelegramInitData с разобранными полями и user-объектом.
    """

    if not init_data:
        raise TelegramAuthError("Пустые данные авторизации Telegram")

    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в окружении")

    data_dict: Dict[str, str] = {}
    hash_value = ""

    # Строка формата: key=value&key2=value2...
    for chunk in init_data.split("&"):
        if not chunk:
            continue

        try:
            key, value = chunk.split("=", 1)
        except ValueError:
            # странный кусок, без '=' — пропускаем
            continue

        if key == "hash":
            hash_value = value
            continue

        # Сохраняем уже *декодированное* значение
        data_dict[key] = unquote(value)

    if not hash_value:
        raise TelegramAuthError("В initData отсутствует параметр hash")

    # Проверяем подпись
    expected_hash = _compute_hash(data_dict, bot_token)
    if expected_hash != hash_value:
        raise TelegramAuthError("Подпись Telegram недействительна")

    # Проверяем "возраст" auth_date
    auth_ts: Optional[int] = None
    if "auth_date" in data_dict:
        try:
            auth_ts = int(data_dict["auth_date"])
            if max_age_seconds > 0:
                now_ts = int(datetime.now(tz=timezone.utc).timestamp())
                if now_ts - auth_ts > max_age_seconds:
                    raise TelegramAuthError("Сессия Telegram истекла")
        except ValueError:
            logger.warning(
                "Не удалось распарсить auth_date: %s",
                data_dict["auth_date"],
            )

    # Разбираем user (JSON)
    user_dict: Optional[Dict[str, Any]] = None
    if "user" in data_dict:
        try:
            user_dict = json.loads(data_dict["user"])
        except json.JSONDecodeError:
            logger.warning("Не удалось распарсить поле user из initData")

    return TelegramInitData(
        raw=init_data,
        data=data_dict,
        user=user_dict,
        auth_date=auth_ts,
    )
