# app/api/v1/profile.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.responses import success_response
from app.models.user import User
from app.schemas.user import UserProfile, UserProfileUpdate
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
