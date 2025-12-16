# app/api/v1/profile.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.middleware import get_current_user
from app.core.responses import success_response
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserProfile, UserProfileUpdate
from app.services.user_service import update_user_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me")
async def get_profile_me(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Возвращает полный профиль текущего пользователя.
    Требует валидной Telegram WebApp авторизации.
    """
    # current_user — это ORM-модель User, поэтому from_attributes=True
    profile = UserProfile.model_validate(current_user, from_attributes=True)
    return success_response(profile.model_dump())


@router.patch("/me")
async def update_profile_me(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Обновляет профиль текущего пользователя.
    """
    updated_user = update_user_profile(db, current_user, data)
    # Возвращаем уже обновлённого пользователя
    profile = UserProfile.model_validate(updated_user, from_attributes=True)
    return success_response(profile.model_dump())
