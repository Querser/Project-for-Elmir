from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.rating import Rating
from app.models.user import User
from app.models.level import Level

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("")
def get_ratings(
    level_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            User.id.label("user_id"),
            User.name.label("user_name"),
            Level.id.label("level_id"),
            Level.title.label("level_title"),
            func.avg(Rating.score).label("avg_score"),
            func.count(Rating.id).label("votes"),
        )
        .join(Rating, Rating.user_id == User.id)
        .outerjoin(Level, Level.id == Rating.level_id)
        .group_by(User.id, User.name, Level.id, Level.title)
        .order_by(func.avg(Rating.score).desc())
    )

    if level_id is not None:
        q = q.filter(Rating.level_id == level_id)

    rows = q.all()
    return [
        {
            "user_id": r.user_id,
            "user_name": r.user_name,
            "level_id": r.level_id,
            "level_title": r.level_title,
            "avg_score": float(r.avg_score) if r.avg_score is not None else 0.0,
            "votes": int(r.votes or 0),
        }
        for r in rows
    ]


@router.get("/levels")
def rating_levels(db: Session = Depends(get_db)):
    levels = db.query(Level).order_by(Level.id.asc()).all()
    return [{"id": l.id, "title": l.title} for l in levels]
