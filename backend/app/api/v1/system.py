# app/api/v1/system.py

from __future__ import annotations

from fastapi import APIRouter, Request, Depends

from app.core.middleware import get_current_user
from app.core.responses import success_response

router = APIRouter()


@router.get("/ping", summary="Проверка работы API без авторизации")
async def ping(request: Request):
    """
    Простейший endpoint, который всегда доступен.

    Нужен для проверки базовой работоспособности API и роутинга /api/v1.
    """
    user_id = getattr(getattr(request.state, "user", None), "id", None)
    return success_response({"message": "pong", "user_id": user_id})


@router.get(
    "/me",
    summary="Информация о текущем пользователе Telegram",
)
async def get_me(user=Depends(get_current_user)):
    """
    Пример защищённого endpoint'а.

    Требует, чтобы middleware успешно определил пользователя по Telegram initData.
    """
    return success_response(
        {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "rating": user.rating,
            "cups": user.cups,
        }
    )
