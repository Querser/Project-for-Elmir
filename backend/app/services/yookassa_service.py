from __future__ import annotations

import base64
import json
import os
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.setting import Setting


YOOKASSA_API_BASE = "https://api.yookassa.ru/v3"


@dataclass(frozen=True)
class YooKassaCredentials:
    shop_id: str
    secret_key: str


def _env_str(name: str) -> str:
    return str(os.getenv(name, "")).strip()


def _setting_str(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).one_or_none()
    if row is None:
        return default
    value = str(getattr(row, "value", "") or "").strip()
    return value or default


def _truthy(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().strip('"').strip("'").lower()
    return normalized in {"1", "true", "yes", "y", "on"}


def payments_enabled(db: Session) -> bool:
    env_value = os.getenv("PAYMENTS_ENABLED")
    if env_value is not None:
        return _truthy(env_value, default=True)

    setting_value = _setting_str(db, "payments_enabled", "true")
    return _truthy(setting_value, default=True)


def get_return_url_default(db: Session) -> str:
    from_env = _env_str("PAYMENT_RETURN_URL")
    if from_env:
        return from_env
    return _setting_str(db, "payment_return_url", "")


def get_credentials(db: Session) -> YooKassaCredentials:
    shop_id = _env_str("PAYMENT_PROVIDER_KEY") or _setting_str(db, "payment_provider_key", "")
    secret_key = _env_str("PAYMENT_PROVIDER_SECRET") or _setting_str(db, "payment_provider_secret", "")

    if not shop_id or not secret_key:
        raise AppException.validation(
            message=(
                "Платежи ЮKassa не настроены. "
                "Укажите PAYMENT_PROVIDER_KEY и PAYMENT_PROVIDER_SECRET "
                "в окружении backend или в admin/settings."
            )
        )

    return YooKassaCredentials(shop_id=shop_id, secret_key=secret_key)


def _auth_header(creds: YooKassaCredentials) -> str:
    token = f"{creds.shop_id}:{creds.secret_key}".encode("utf-8")
    return f"Basic {base64.b64encode(token).decode('ascii')}"


def _provider_message(payload: dict[str, Any] | None, fallback: str) -> str:
    if not payload:
        return fallback
    for key in ("description", "message", "error_description", "type"):
        value = payload.get(key)
        if value:
            return str(value)
    return fallback


def _request_json(
    creds: YooKassaCredentials,
    *,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    idempotence_key: str | None = None,
) -> dict[str, Any]:
    url = f"{YOOKASSA_API_BASE}{path}"
    body = None
    headers = {
        "Authorization": _auth_header(creds),
        "Accept": "application/json",
    }

    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    if idempotence_key:
        headers["Idempotence-Key"] = idempotence_key

    request = Request(url=url, data=body, headers=headers, method=method.upper())

    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = ""
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        parsed = None
        try:
            parsed = json.loads(raw) if raw else None
        except Exception:
            parsed = None

        details = {
            "provider_status": int(exc.code),
            "provider_payload": parsed if parsed is not None else raw,
        }
        message = _provider_message(parsed, f"ЮKassa HTTP {exc.code}")

        if int(exc.code) in {401, 403}:
            raise AppException.forbidden(
                message=(
                    "ЮKassa отклонила авторизацию. "
                    "Проверьте shop_id и secret key."
                ),
                details=details,
            )
        if int(exc.code) == 404:
            raise AppException.not_found(message="Платеж ЮKassa не найден", details=details)
        raise AppException.conflict(message=message, details=details)
    except URLError as exc:
        raise AppException.conflict(
            message="Не удалось подключиться к ЮKassa. Попробуйте позже.",
            details={"reason": str(exc)},
        )


def _format_amount(value: Decimal | float | int | str) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{amount:.2f}"


def create_redirect_payment(
    db: Session,
    *,
    amount_rub: Decimal | float | int | str,
    description: str,
    return_url: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    creds = get_credentials(db)
    payload = {
        "amount": {
            "value": _format_amount(amount_rub),
            "currency": "RUB",
        },
        "confirmation": {
            "type": "redirect",
            "return_url": str(return_url).strip(),
        },
        "capture": True,
        "description": str(description).strip()[:128] or "Оплата тренировки",
        "metadata": metadata or {},
    }
    return _request_json(
        creds,
        method="POST",
        path="/payments",
        payload=payload,
        idempotence_key=str(uuid.uuid4()),
    )


def get_payment(db: Session, *, provider_payment_id: str) -> dict[str, Any]:
    creds = get_credentials(db)
    payment_id = str(provider_payment_id or "").strip()
    if not payment_id:
        raise AppException.validation(message="Некорректный payment_id")
    return _request_json(
        creds,
        method="GET",
        path=f"/payments/{payment_id}",
    )

