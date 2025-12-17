# app/api/v1/levels.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.db.session import get_db
from app.schemas.level import LevelDTO
from app.services.level_service import get_all_levels

router = APIRouter(prefix="/levels", tags=["levels"])


@router.get("")
async def list_levels(
    db: Session = Depends(get_db),
) -> dict:
    """
    Список уровней (для подсказок и заполнения профиля).

    GET /api/v1/levels
    Ответ: { "items": [ {id, name, description}, ... ] }
    """
    levels = get_all_levels(db)
    items = [
        LevelDTO.model_validate(level, from_attributes=True).model_dump()
        for level in levels
    ]
    return success_response({"items": items})
