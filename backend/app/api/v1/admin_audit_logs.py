from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user_any, get_db
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.services.audit_log_service import list_audit_logs

router = APIRouter(prefix="/admin/audit-logs", tags=["admin-audit-logs"])


def _to_schema(cls, obj):
    if hasattr(cls, "model_validate"):
        return cls.model_validate(obj, from_attributes=True)
    if hasattr(cls, "from_orm"):
        return cls.from_orm(obj)
    return cls(**obj)


def _dump(model):
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


@router.get("", response_model=dict)
def admin_audit_logs_list(
    limit: int = 50,
    offset: int = 0,
    user_id: int | None = None,
    action: str | None = None,
    entity: str | None = None,
    entity_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    training_id: int | None = None,
    db: Session = Depends(get_db),
    _admin: Any = Depends(get_current_admin_user_any),
):
    items, total = list_audit_logs(
        db,
        limit=limit,
        offset=offset,
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
        training_id=training_id,
    )

    dto_items = [_to_schema(AuditLogResponse, x) for x in items]
    result = AuditLogListResponse(items=dto_items, total=total, limit=limit, offset=offset)
    return {"ok": True, "result": _dump(result), "error": None}
