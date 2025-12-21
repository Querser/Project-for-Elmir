# app/api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1 import (
    system,
    profile,
    trainings,
    enrollments,
    levels,
    ratings,
    admin_billing,
)

api_router = APIRouter()

# Системные/тестовые ручки
api_router.include_router(system.router, tags=["system"])

# Роуты профиля пользователя
api_router.include_router(profile.router, tags=["profile"])

# Роуты тренировок и расписания
api_router.include_router(trainings.router)

# Роуты записей на тренировки
api_router.include_router(enrollments.router)

# Справочник уровней
api_router.include_router(levels.router)

# Рейтинг игроков
api_router.include_router(ratings.router)

# Админские ручки по долгам/банам
api_router.include_router(admin_billing.router)
