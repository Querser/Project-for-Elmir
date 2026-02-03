# app/api/v1/profile.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.core.deps import get_db, get_current_user
from app.core.responses import success_response
from app.models.user import User
from app.schemas.user import UserProfile, UserProfileUpdate, UserPublicProfile
from app.services.user_service import update_user_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me")
def get_profile_me(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Возвращает полный профиль текущего пользователя.
    """
    profile = UserProfile.model_validate(current_user, from_attributes=True)
    return success_response(profile.model_dump())


def _update_profile_impl(
    data: UserProfileUpdate,
    db: Session,
    current_user: User,
) -> dict:
    """
    Общая реализация для PATCH и PUT.
    """
    updated_user = update_user_profile(db, current_user, data)
    profile = UserProfile.model_validate(updated_user, from_attributes=True)
    return success_response(profile.model_dump())


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
    PUT: оставляем как алиас к PATCH, чтобы фронт не ловил 405.
    """
    return _update_profile_impl(data=data, db=db, current_user=current_user)


@router.get("/{user_id}")
def get_public_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    is_self = user.id == current_user.id
    username = user.username if (is_self or user.is_telegram_public) else None

    payload = UserPublicProfile(
        id=user.id,
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