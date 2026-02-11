from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user_any, get_db
from app.core.responses import success_response
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/basic", response_model=dict)
def get_basic_metrics(
    db: Session = Depends(get_db),
    _admin: Any = Depends(get_current_admin_user_any),
) -> dict:
    return success_response(MetricsService.snapshot(db))

