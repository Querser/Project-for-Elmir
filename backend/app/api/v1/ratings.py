# app/api/v1/ratings.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.middleware import get_current_user
from app.core.responses import success_response
from app.db.session import get_db
from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.rating import (
    RatingUserDTO,
    RatingLeaderboardResponse,
    RatingUserInfoDTO,
)
from app.services.rating_service import (
    get_leaderboard as get_leaderboard_service,
    get_user_position,
    get_total_active_users,
)

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("/leaderboard")
async def get_leaderboard(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """
    Таблица лидеров.

    GET /api/v1/ratings/leaderboard?limit=...&offset=...

    Возвращает пользователей, отсортированных по rating, cups.
    """
    users, total = get_leaderboard_service(db, limit=limit, offset=offset)

    items: list[RatingUserDTO] = []
    for idx, user in enumerate(users):
        dto = RatingUserDTO(
            position=offset + idx + 1,
            user_id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            rating=user.rating,
            cups=user.cups,
            level_id=user.level_id,
        )
        items.append(dto)

    response = RatingLeaderboardResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    ).model_dump()

    return success_response(response)


@router.get("/me")
async def get_my_rating(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Информация о рейтинге ТЕКУЩЕГО пользователя.

    GET /api/v1/ratings/me
    """
    position = get_user_position(db, current_user)
    total = get_total_active_users(db)

    dto = RatingUserInfoDTO(
        user_id=current_user.id,
        position=position,
        total=total,
        rating=current_user.rating,
        cups=current_user.cups,
        level_id=current_user.level_id,
    ).model_dump()

    return success_response(dto)


@router.get("/user/{user_id}")
async def get_user_rating(
    user_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Информация о рейтинге произвольного игрока по ID.

    GET /api/v1/ratings/user/{user_id}
    """
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise AppException(
            error_code="NOT_FOUND",
            message="Пользователь не найден",
        )

    position = get_user_position(db, user)
    total = get_total_active_users(db)

    dto = RatingUserInfoDTO(
        user_id=user.id,
        position=position,
        total=total,
        rating=user.rating,
        cups=user.cups,
        level_id=user.level_id,
    ).model_dump()

    return success_response(dto)
