# app/api/v1/profile.py
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.core.deps import get_db, get_current_user
from app.core.exceptions import AppException
from app.core.responses import success_response
from app.models.user import User
from app.schemas.user import UserProfile, UserProfileUpdate, UserPublicProfile
from app.services.ban_service import get_active_ban
from app.services.user_service import update_user_profile

router = APIRouter(prefix="/profile", tags=["profile"])

_ALLOWED_AVATAR_PREFIXES = ("image/",)
_MAX_AVATAR_BYTES = 10 * 1024 * 1024
_AVATARS_ROOT = Path(__file__).resolve().parents[3] / "media" / "avatars"
_AVATARS_URL_PREFIX = "/media/avatars/"


def _active_ban_payload(db: Session, user_id: int) -> tuple[bool, str | None, object | None]:
    active_ban = get_active_ban(db, user_id=user_id)
    if active_ban is None:
        return False, None, None
    return True, (active_ban.reason or None), active_ban.until


def _profile_dump(db: Session, user: User) -> dict:
    profile = UserProfile.model_validate(user, from_attributes=True).model_dump()
    has_active_ban, active_ban_reason, active_ban_until = _active_ban_payload(db, user.id)
    profile["has_active_ban"] = has_active_ban
    profile["active_ban_reason"] = active_ban_reason
    profile["active_ban_until"] = active_ban_until
    return profile


def _avatar_extension(upload: UploadFile) -> str:
    filename = (upload.filename or "").strip()
    suffix = Path(filename).suffix.lower()
    if suffix and len(suffix) <= 10 and suffix.replace(".", "").isalnum():
        return suffix

    content_type = (upload.content_type or "").lower()
    if content_type == "image/jpeg":
        return ".jpg"
    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    if content_type == "image/gif":
        return ".gif"
    return ".bin"


def _local_avatar_path_from_url(avatar_url: str | None) -> Path | None:
    current = (avatar_url or "").strip()
    if not current.startswith(_AVATARS_URL_PREFIX):
        return None
    rel = current[len(_AVATARS_URL_PREFIX):].strip()
    if not rel:
        return None
    return _AVATARS_ROOT / rel


@router.get("/me")
def get_profile_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Возвращает полный профиль текущего пользователя.
    """
    user = db.query(User).filter(User.id == current_user.id).one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Пользователь не найден"}},
        )
    return success_response(_profile_dump(db, user))


def _update_profile_impl(
    data: UserProfileUpdate,
    db: Session,
    current_user: User,
) -> dict:
    """
    Общая реализация для PATCH и PUT.
    """
    updated_user = update_user_profile(db, current_user, data)
    return success_response(_profile_dump(db, updated_user))


@router.patch("/me")
def update_profile_me_patch(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    PATCH: частичное обновление профиля.
    """
    return _update_profile_impl(data=data, db=db, current_user=current_user)


@router.put("/me")
def update_profile_me_put(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    PUT: alias к PATCH, чтобы фронт не ловил 405.
    """
    return _update_profile_impl(data=data, db=db, current_user=current_user)


@router.post("/me/avatar", response_model=dict)
async def upload_profile_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    content_type = (file.content_type or "").lower().strip()
    if not any(content_type.startswith(prefix) for prefix in _ALLOWED_AVATAR_PREFIXES):
        raise AppException.validation("Разрешены только image/* файлы")

    data = await file.read()
    if not data:
        raise AppException.validation("Файл пустой")
    if len(data) > _MAX_AVATAR_BYTES:
        raise AppException.validation("Файл слишком большой (максимум 10 МБ)")

    user = db.query(User).filter(User.id == current_user.id).one_or_none()
    if user is None:
        raise AppException.not_found(message="Пользователь не найден")

    old_local_avatar = _local_avatar_path_from_url(getattr(user, "avatar_url", None))

    _AVATARS_ROOT.mkdir(parents=True, exist_ok=True)
    extension = _avatar_extension(file)
    filename = f"{uuid4().hex}{extension}"
    destination = _AVATARS_ROOT / filename
    destination.write_bytes(data)

    user.avatar_url = f"{_AVATARS_URL_PREFIX}{filename}"
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        if old_local_avatar and old_local_avatar.exists() and old_local_avatar != destination:
            old_local_avatar.unlink()
    except Exception:
        # Удаление старого файла не должно ломать успешную смену аватара.
        pass

    return success_response(_profile_dump(db, user))


@router.delete("/me/avatar", response_model=dict)
def delete_profile_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    user = db.query(User).filter(User.id == current_user.id).one_or_none()
    if user is None:
        raise AppException.not_found(message="Пользователь не найден")

    old_local_avatar = _local_avatar_path_from_url(getattr(user, "avatar_url", None))

    user.avatar_url = None
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        if old_local_avatar and old_local_avatar.exists():
            old_local_avatar.unlink()
    except Exception:
        pass

    return success_response(_profile_dump(db, user))


@router.get("/{user_id}")
def get_public_profile(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """
    Публичный профиль другого пользователя (для раздела "Рейтинг").

    Показываем:
    - имя
    - уровень
    - рейтинг
    - кубки
    - Telegram username (ТОЛЬКО если пользователь разрешил)
    """

    user = (
        db.query(User)
        .options(selectinload(User.level))
        .filter(User.id == user_id)
        .one_or_none()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Пользователь не найден"}},
        )

    username = user.username if user.is_telegram_public else None

    payload = UserPublicProfile(
        id=user.id,
        avatar_url=getattr(user, "avatar_url", None),
        first_name=user.first_name,
        last_name=user.last_name,
        level_id=user.level_id,
        level_name=(user.level.name if user.level else None),
        rating=user.rating,
        cups=user.cups,
        username=username,
        is_telegram_public=bool(user.is_telegram_public),
    )

    return success_response(payload.model_dump())
