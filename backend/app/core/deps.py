# backend/app/core/deps.py
from __future__ import annotations

from typing import Any, Generator, Optional, Type

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

# ----------------------------
# DB dependency
# ----------------------------
SessionLocal = None

try:
    # Частый вариант: backend/app/db/session.py
    from app.db.session import SessionLocal as _SessionLocal  # type: ignore
    SessionLocal = _SessionLocal
except Exception:
    pass

if SessionLocal is None:
    try:
        # Другой вариант: backend/app/database.py
        from app.database import SessionLocal as _SessionLocal  # type: ignore
        SessionLocal = _SessionLocal
    except Exception:
        pass


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError(
            "SessionLocal не найден. Проверь, где у тебя создаётся DB-сессия, "
            "и поправь импорты в backend/app/core/deps.py (секция DB dependency)."
        )

    db: Session = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass


# ----------------------------
# User model import helper
# ----------------------------
_USER_MODEL: Optional[Type[Any]] = None


def _get_user_model() -> Type[Any]:
    """
    Пытаемся найти User-модель в типичных местах.
    """
    global _USER_MODEL
    if _USER_MODEL is not None:
        return _USER_MODEL

    candidates = (
        "app.models.user",
        "app.models.users",
        "app.models",
    )

    last_err: Exception | None = None
    for mod in candidates:
        try:
            m = __import__(mod, fromlist=["User"])
            User = getattr(m, "User", None)
            if User is not None:
                _USER_MODEL = User
                return _USER_MODEL
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Не смог импортировать модель User. Последняя ошибка: {last_err}")


# ----------------------------
# Auth dependencies (DEV)
# ----------------------------
def _parse_int(v: str | None) -> int | None:
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _get_user_from_headers(request: Request) -> tuple[int | None, int | None]:
    """
    Поддерживаем 2 варианта:
    - X-User-Id: 123
    - X-Telegram-Id: 123456789
    """
    user_id = _parse_int(request.headers.get("X-User-Id"))
    tg_id = _parse_int(request.headers.get("X-Telegram-Id"))
    return user_id, tg_id


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Any | None:
    """
    Мягкая авторизация: если заголовков нет/юзер не найден — возвращаем None.
    """
    user_id, tg_id = _get_user_from_headers(request)
    if user_id is None and tg_id is None:
        return None

    User = _get_user_model()

    q = db.query(User)
    if user_id is not None:
        user = q.filter(User.id == user_id).first()
        return user

    if tg_id is not None:
        user = q.filter(User.telegram_id == tg_id).first()
        return user

    return None


def get_current_user(
    user: Any | None = Depends(get_current_user_optional),
) -> Any:
    """
    Жёсткая авторизация: если юзера нет — 401.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: provide X-User-Id or X-Telegram-Id header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _user_is_admin(user: Any) -> bool:
    if user is None:
        return False

    # ORM-модель
    if hasattr(user, "is_admin"):
        return bool(getattr(user, "is_admin"))

    # На всякий случай dict
    if isinstance(user, dict):
        return bool(user.get("is_admin"))

    return False


def get_current_admin_user(
    user: Any = Depends(get_current_user),
) -> Any:
    if not _user_is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user
