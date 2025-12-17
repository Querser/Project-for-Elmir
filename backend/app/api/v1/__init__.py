# app/api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1 import (
    system,
    profile,
    trainings,
    enrollments,
    levels,
    ratings,
)

api_router = APIRouter()

# Системные/тестовые ручки
api_router.include_router(system.router, tags=["system"])

# Профиль пользователя
api_router.include_router(profile.router, tags=["profile"])

# Тренировки и расписание
api_router.include_router(trainings.router)

# Записи на тренировки (основа/резерв)
api_router.include_router(enrollments.router)

# Справочник уровней
api_router.include_router(levels.router)

# Рейтинг игроков
api_router.include_router(ratings.router)
