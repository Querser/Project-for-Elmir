# backend/app/api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1 import system, profile, trainings

api_router = APIRouter()

# Системные/тестовые ручки
api_router.include_router(system.router, tags=["system"])

# Роуты профиля пользователя
api_router.include_router(profile.router, tags=["profile"])

# Роуты тренировок и расписания
api_router.include_router(trainings.router)
