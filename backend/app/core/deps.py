# app/core/deps.py
from __future__ import annotations

import hmac
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Generator, Optional, Union, Any
from urllib.parse import parse_qsl
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# ---- imports: подстройка под твой проект (с фолбэками) ----
try:
    from app.db.session import SessionLocal  # type: ignore
except Exception:
    from app.database import SessionLocal  # type: ignore

try:
    from app.models.user import User  # type: ignore
except Exception:
    from app.db.models import User  # type: ignore


# -----------------------------
# Admin token imports (stage 13)
# -----------------------------
try:
    from app.core.admin_tokens import verify_admin_access_token, AdminTokenError  # type: ignore
except Exception:  # pragma: no cover
    verify_admin_access_token = None  # type: ignore

    class AdminTokenError(Exception):  # type: ignore
        pass


# -----------------------------
# Error helpers (под формат {"error": {...}})
# -----------------------------
def _http_error(
    code: str,
    message: str,
    status_code: int,
    details: Optional[dict] = None,
) -> HTTPException:
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return HTTPException(status_code=status_code, detail=payload)


def unauthorized(message: str, required_header: Optional[str] = None) -> HTTPException:
    details = {"required_header": required_header} if required_header else None
    return _http_error("unauthorized", message, status.HTTP_401_UNAUTHORIZED, details)


def forbidden(message: str) -> HTTPException:
    return _http_error("forbidden", message, status.HTTP_403_FORBIDDEN)


def internal_error(message: str = "Internal Server Error") -> HTTPException:
    return _http_error("internal_error", message, status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------------
# DB dependency
# -----------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# Telegram WebApp initData verify
# -----------------------------
@dataclass(frozen=True)
class TgWebAppUser:
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


def _get_env_bot_token() -> Optional[str]:
    return (
        os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("BOT_TOKEN")
        or os.getenv("TG_BOT_TOKEN")
    )


def _verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """
    Валидация Telegram WebApp initData (официальный алгоритм HMAC SHA256).
    """
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.get("hash")
    if not received_hash:
        raise unauthorized(
            "Пользователь не авторизован через Telegram",
            required_header="X-Telegram-Init-Data",
        )

    data_check_items = []
    for k in sorted(pairs.keys()):
        if k == "hash":
            continue
        data_check_items.append(f"{k}={pairs[k]}")
    data_check_string = "\n".join(data_check_items)

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc_hash, received_hash):
        raise unauthorized(
            "Пользователь не авторизован через Telegram",
            required_header="X-Telegram-Init-Data",
        )

    return pairs


def _parse_tg_user_from_init_data(init_data_pairs: dict) -> TgWebAppUser:
    raw_user = init_data_pairs.get("user")
    if not raw_user:
        raise unauthorized("Пользователь не авторизован через Telegram", required_header="X-Telegram-Init-Data")

    try:
        user_obj = json.loads(raw_user)
    except Exception:
        raise unauthorized("Пользователь не авторизован через Telegram", required_header="X-Telegram-Init-Data")

    if "id" not in user_obj:
        raise unauthorized("Пользователь не авторизован через Telegram", required_header="X-Telegram-Init-Data")

    return TgWebAppUser(
        telegram_id=int(user_obj["id"]),
        username=user_obj.get("username"),
        first_name=user_obj.get("first_name"),
        last_name=user_obj.get("last_name"),
    )


# -----------------------------
# Helpers: env parsing / dev-mode
# -----------------------------
def _strip_wrapping_quotes(value: str) -> str:
    """
    Снимаем внешние кавычки ПОВТОРНО:
      "'172'" -> 172
      "\"172\"" -> 172
      " '172' " -> 172
    """
    v = (value or "").strip()
    while len(v) >= 2 and v[0] == v[-1] and v[0] in {"'", '"'}:
        v = v[1:-1].strip()
    return v


def _env_truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    v = _strip_wrapping_quotes(v).strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def _env_is_dev_environment() -> bool:
    env = _strip_wrapping_quotes(os.getenv("ENVIRONMENT") or "").strip().lower()
    return env in {"dev", "development", "local"}


def _allow_insecure_header_auth() -> bool:
    if "ALLOW_INSECURE_HEADER_AUTH" in os.environ:
        return _env_truthy("ALLOW_INSECURE_HEADER_AUTH", default=False)

    if _env_truthy("DEV_AUTO_CREATE_USER_FROM_HEADER", default=False):
        return True

    if _env_is_dev_environment():
        return True

    return False


def _get_dev_default_telegram_id() -> Optional[int]:
    raw = os.getenv("DEV_DEFAULT_TELEGRAM_ID")
    if raw is None:
        return None
    raw = _strip_wrapping_quotes(str(raw))
    if not raw:
        return None

    if not re.fullmatch(r"-?\d+", raw):
        log.error("DEV_DEFAULT_TELEGRAM_ID is set but invalid: %r", raw)
        return None

    try:
        return int(raw)
    except Exception:
        log.error("DEV_DEFAULT_TELEGRAM_ID is set but invalid: %r", raw)
        return None


def _dev_mode_enabled() -> bool:
    if _allow_insecure_header_auth():
        return True
    if _get_dev_default_telegram_id() is not None:
        return True
    return False


def _get_header(request: Request, name: str) -> Optional[str]:
    v = request.headers.get(name)
    if not v:
        return None
    v = v.strip()
    return v or None


def _parse_user_id(value: str) -> Union[int, UUID]:
    value = value.strip()
    if value.isdigit():
        return int(value)
    return UUID(value)


def _parse_int(value: str) -> int:
    return int(_strip_wrapping_quotes(value).strip())


# -----------------------------
# Current user helpers
# -----------------------------
def _get_or_create_user_by_telegram(db: Session, tg: TgWebAppUser) -> User:
    try:
        user = db.execute(select(User).where(User.telegram_id == tg.telegram_id)).scalar_one_or_none()
        if user:
            if tg.username is not None and hasattr(user, "username") and getattr(user, "username", None) != tg.username:
                user.username = tg.username
                db.add(user)
                db.commit()
                db.refresh(user)
            return user

        user = User(telegram_id=tg.telegram_id)
        if hasattr(user, "username"):
            user.username = tg.username

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    except IntegrityError:
        db.rollback()
        user = db.execute(select(User).where(User.telegram_id == tg.telegram_id)).scalar_one_or_none()
        if user:
            return user
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def _get_user_by_id(db: Session, user_id: Union[int, UUID]) -> Optional[User]:
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def _get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    return db.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one_or_none()


# -----------------------------
# Dependency: require initData OR dev header
# -----------------------------
def require_telegram_init_data_or_dev_header(request: Request) -> None:
    if _get_header(request, "X-Telegram-Init-Data"):
        return

    if _dev_mode_enabled():
        if _get_header(request, "X-Telegram-Id") or _get_header(request, "X-User-Id") or (_get_dev_default_telegram_id() is not None):
            return

    raise unauthorized("Пользователь не авторизован через Telegram", required_header="X-Telegram-Init-Data")


# -----------------------------
# Main auth dependency
# -----------------------------
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    try:
        init_data = _get_header(request, "X-Telegram-Init-Data")
        if init_data:
            bot_token = _get_env_bot_token()
            if not bot_token or bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
                raise unauthorized("Не настроен TELEGRAM_BOT_TOKEN для проверки Telegram initData")
            pairs = _verify_telegram_init_data(init_data, bot_token)
            tg_user = _parse_tg_user_from_init_data(pairs)
            return _get_or_create_user_by_telegram(db, tg_user)

        # ---- DEV ветка ----
        if _dev_mode_enabled():
            user_id_raw = _get_header(request, "X-User-Id")
            if user_id_raw:
                try:
                    user_id = _parse_user_id(user_id_raw)
                except Exception:
                    raise unauthorized("Unauthorized: invalid X-User-Id header", required_header="X-User-Id")

                user = _get_user_by_id(db, user_id)
                if not user:
                    raise unauthorized("Unauthorized: user not found for X-User-Id header", required_header="X-User-Id")
                return user

            tg_id_raw = _get_header(request, "X-Telegram-Id")
            if tg_id_raw:
                try:
                    tg_id = _parse_int(tg_id_raw)
                except Exception:
                    raise unauthorized("Unauthorized: invalid X-Telegram-Id header", required_header="X-Telegram-Id")

                user = _get_user_by_telegram_id(db, tg_id)
                if user:
                    return user
                return _get_or_create_user_by_telegram(db, TgWebAppUser(telegram_id=tg_id))

            default_tg_id = _get_dev_default_telegram_id()
            if default_tg_id is not None:
                return _get_or_create_user_by_telegram(db, TgWebAppUser(telegram_id=default_tg_id))

            raise unauthorized("Unauthorized: provide X-User-Id, X-Telegram-Id or X-Telegram-Init-Data header")

        # ---- PROD ветка ----
        raise unauthorized("Пользователь не авторизован через Telegram", required_header="X-Telegram-Init-Data")

    except HTTPException:
        raise
    except Exception as e:
        log.exception("Unhandled error in get_current_user: %s", e)
        raise internal_error("Ошибка авторизации (см. логи backend)")


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    init_data = _get_header(request, "X-Telegram-Init-Data")
    user_id_raw = _get_header(request, "X-User-Id")
    tg_id_raw = _get_header(request, "X-Telegram-Id")

    if not init_data and not user_id_raw and not tg_id_raw:
        if _dev_mode_enabled() and (_get_dev_default_telegram_id() is not None):
            return get_current_user(request=request, db=db)
        return None

    return get_current_user(request=request, db=db)


# -----------------------------
# Admin dependencies (telegram-admin mode)
# -----------------------------
def _is_admin_user(user: User) -> bool:
    if hasattr(user, "is_admin") and bool(getattr(user, "is_admin")):
        return True

    if hasattr(user, "role"):
        role = getattr(user, "role")
        if isinstance(role, str) and role.lower() in {"admin", "superadmin"}:
            return True

    raw = _strip_wrapping_quotes((os.getenv("DEV_ADMIN_TELEGRAM_IDS") or "").strip())
    if raw and hasattr(user, "telegram_id") and getattr(user, "telegram_id", None) is not None:
        try:
            allowed = {int(_strip_wrapping_quotes(x.strip())) for x in raw.split(",") if x.strip()}
            return int(user.telegram_id) in allowed
        except Exception:
            return False

    return False


def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if not _is_admin_user(user):
        raise forbidden("Недостаточно прав")
    return user


require_admin = get_current_admin_user


# -----------------------------
# Admin dependencies (bearer-token mode for admin panel)
# -----------------------------
@dataclass(frozen=True)
class AdminPrincipal:
    username: str


def _get_bearer_token(request: Request) -> Optional[str]:
    raw = request.headers.get("Authorization")
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    if raw.lower().startswith("bearer "):
        token = raw[7:].strip()
        return token or None
    return None


def get_current_admin_principal(
    request: Request,
) -> AdminPrincipal:
    """
    Только Bearer access token (для админ-панели).
    """
    token = _get_bearer_token(request)
    if not token:
        raise unauthorized("Требуется Bearer access token", required_header="Authorization: Bearer <access_token>")

    if verify_admin_access_token is None:
        raise internal_error("Admin token module is not configured (admin_tokens.py missing)")

    try:
        payload = verify_admin_access_token(token)
    except AdminTokenError:
        raise unauthorized("Неверный или просроченный access token", required_header="Authorization: Bearer <access_token>")
    except Exception:
        log.exception("Unhandled error while verifying admin token")
        raise unauthorized("Неверный или просроченный access token", required_header="Authorization: Bearer <access_token>")

    username = str(payload.get("username") or payload.get("sub") or "admin")
    return AdminPrincipal(username=username)


def get_current_admin_user_any(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """
    Гибрид:
    - если есть Authorization: Bearer ... -> токенная админка
    - иначе -> старый механизм (Telegram initData/dev headers + проверка админа)
    """
    token = _get_bearer_token(request)
    if token:
        return get_current_admin_principal(request=request)

    # fallback to старой авторизации
    user = get_current_user(request=request, db=db)
    if not _is_admin_user(user):
        raise forbidden("Недостаточно прав")
    return user


require_admin_any = get_current_admin_user_any
