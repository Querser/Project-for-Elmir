from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.responses import success_response
from app.models.user import User
from app.services.rating_service import get_leaderboard, get_user_position, get_total_active_users

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("", response_model=dict)
def leaderboard(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/ratings
    Возвращает список игроков по рейтингу (rating, cups).
    """
    users, total = get_leaderboard(db, limit=limit, offset=offset)

    items = []
    for i, u in enumerate(users, start=offset + 1):
        # username в списке отдаём только если пользователь разрешил
        username = u.username if u.is_telegram_public else None

        items.append(
            {
                "place": i,
                "user_id": u.id,
                "telegram_id": u.telegram_id,
                "username": username,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "rating": u.rating,
                "cups": u.cups,
                "level_id": u.level_id,
            }
        )

    return success_response(
        {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/me", response_model=dict)
def my_rating(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    GET /api/v1/ratings/me
    Место текущего пользователя в рейтинге.
    """
    position = get_user_position(db, user)
    total = get_total_active_users(db)

    return success_response(
        {
            "user_id": user.id,
            "rating": user.rating,
            "cups": user.cups,
            "level_id": user.level_id,  # ✅ нужно для "Мой уровень" на фронте
            "position": position,
            "total_users": total,
        }
    )