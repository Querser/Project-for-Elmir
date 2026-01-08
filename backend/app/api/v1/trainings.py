from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_admin_user, get_current_user_optional
from app.schemas.training import TrainingCreate, TrainingUpdate
from app.schemas.training_ui import TrainingReadUI, TrainingsPageUI
from app.services.training_service import (
    cancel_training,
    create_training,
    delete_training,
    get_training_or_404,
    list_trainings,
    update_training,
)
from app.services.training_ui_service import build_training_ui_payload

router = APIRouter(prefix="/trainings", tags=["trainings"])


def _normalize_json(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, datetime):
        return v
    if isinstance(v, list):
        return [_normalize_json(x) for x in v]
    if isinstance(v, tuple):
        return [_normalize_json(x) for x in v]
    if isinstance(v, dict):
        return {k: _normalize_json(val) for k, val in v.items()}
    return v


def _price_tier_to_dict(pt: Any) -> dict[str, Any]:
    return {
        "id": getattr(pt, "id", None),
        "training_id": getattr(pt, "training_id", None),
        "title": getattr(pt, "title", ""),
        "price": _normalize_json(getattr(pt, "price", None)),
        "sort_order": getattr(pt, "sort_order", 0),
        "level_id": getattr(pt, "level_id", None),
    }


def _training_to_dict(t: Any) -> dict[str, Any]:
    pts = getattr(t, "price_tiers", []) or []
    pts_dict = [_price_tier_to_dict(x) for x in pts]
    pts_dict.sort(key=lambda x: (x.get("sort_order") or 0, x.get("id") or 0))

    return {
        "id": getattr(t, "id", None),
        "title": getattr(t, "title", ""),
        "description": getattr(t, "description", None),
        "start_at": getattr(t, "start_at", None),
        "duration_minutes": getattr(t, "duration_minutes", None),
        "min_level_name": getattr(t, "min_level_name", None),
        "max_level_name": getattr(t, "max_level_name", None),
        "price": _normalize_json(getattr(t, "price", None)),
        "capacity_main": getattr(t, "capacity_main", None),
        "capacity_reserve": getattr(t, "capacity_reserve", None),
        "coach_name": getattr(t, "coach_name", None),
        "image_url": getattr(t, "image_url", None),
        "video_url": getattr(t, "video_url", None),
        "location_id": getattr(t, "location_id", None),
        "is_cancelled": bool(getattr(t, "is_cancelled", False)),
        "price_tiers": pts_dict,
    }


def _to_training_read_ui_payload(db: Session, training_obj: Any, user: Any | None) -> dict[str, Any]:
    base = _normalize_json(_training_to_dict(training_obj))
    ui = _normalize_json(build_training_ui_payload(db, training_obj, user))
    base.update(ui)
    return base


# ✅ ВАЖНО: СТАТИЧЕСКИЕ РОУТЫ ВЫШЕ ДИНАМИЧЕСКИХ

@router.get("/admin", response_model=TrainingsPageUI)
def list_admin_trainings(
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    items, total = list_trainings(
        db,
        include_cancelled=True,
        limit=limit,
        offset=skip,
    )
    payload = [_to_training_read_ui_payload(db, t, None) for t in (items or [])]
    return {"items": payload, "total": total, "limit": limit, "offset": skip}


@router.post("", response_model=TrainingReadUI)
def create_training_admin(
    payload: TrainingCreate,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user),
):
    created = create_training(db=db, data=payload)
    return _to_training_read_ui_payload(db, created, None)


@router.patch("/{training_id}", response_model=TrainingReadUI)
def update_training_admin(
    training_id: int,
    payload: TrainingUpdate,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user),
):
    training = get_training_or_404(db=db, training_id=training_id)
    updated = update_training(db=db, training=training, data=payload)
    return _to_training_read_ui_payload(db, updated, None)


@router.delete("/{training_id}", response_model=dict)
def delete_training_admin(
    training_id: int,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user),
):
    training = get_training_or_404(db=db, training_id=training_id)
    delete_training(db=db, training=training)
    return {"ok": True}


@router.post("/{training_id}/cancel", response_model=TrainingReadUI)
def cancel_training_admin(
    training_id: int,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user),
):
    training = get_training_or_404(db=db, training_id=training_id)
    cancelled = cancel_training(db=db, training=training)
    return _to_training_read_ui_payload(db, cancelled, None)


@router.get("", response_model=TrainingsPageUI)
def list_public_trainings(
    db: Session = Depends(get_db),
    user: Any | None = Depends(get_current_user_optional),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    now_utc = datetime.now(timezone.utc)

    items, total = list_trainings(
        db,
        date_from=now_utc,
        include_cancelled=False,
        limit=limit,
        offset=skip,
    )

    payload = [_to_training_read_ui_payload(db, t, user) for t in (items or [])]
    return {"items": payload, "total": total, "limit": limit, "offset": skip}


@router.get("/{training_id}", response_model=TrainingReadUI)
def get_public_training(
    training_id: int,
    db: Session = Depends(get_db),
    user: Any | None = Depends(get_current_user_optional),
):
    training = get_training_or_404(db=db, training_id=training_id)

    if bool(getattr(training, "is_cancelled", False)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")

    return _to_training_read_ui_payload(db, training, user)
