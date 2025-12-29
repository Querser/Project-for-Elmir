# backend/app/core/deps.py
from __future__ import annotations

import os
from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import TelegramInitDataError, verify_telegram_init_data
from app.db.session import async_session_maker
from app.models.user import User


def _get_bot_token() -> str:
    """
    Берём токен максимально безопасно и совместимо со старыми конфигами:
    1) пробуем несколько возможных имён в settings
    2) пробуем TELEGRAM_BOT_TOKEN из env (у тебя он точно есть внутри контейнера)
    """
    for attr in ("TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TELEGRAM_TOKEN", "TG_BOT_TOKEN"):
        if hasattr(settings, attr):
            val = getattr(settings, attr)
            if isinstance(val, str) and val.strip():
                return val.strip()

    env_val = os.getenv("TELEGRAM_BOT_TOKEN")
    if env_val and env_val.strip():
        return env_val.strip()

    raise RuntimeError(
        "Bot token not found. Expected settings.TELEGRAM_BOT_TOKEN (or BOT_TOKEN/TELEGRAM_TOKEN/TG_BOT_TOKEN) "
        "or env TELEGRAM_BOT_TOKEN"
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    x_telegram_init_data: Optional[str] = Header(default=None, alias="X-Telegram-Init-Data"),
) -> User:
    if not x_telegram_init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Telegram-Init-Data header",
        )

    bot_token = _get_bot_token()

    try:
        payload = verify_telegram_init_data(x_telegram_init_data, bot_token)
    except TelegramInitDataError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e

    user_data = payload.get("user") or {}
    tg_id = user_data.get("id")
    if not tg_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram user id is missing")

    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=tg_id,
            username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user
