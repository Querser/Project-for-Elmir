from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.services.audit_log_service import list_audit_logs

router = APIRouter(prefix="/admin/audit-logs", tags=["admin-audit-logs"])


@router.get("", response_model=dict)
async def admin_audit_logs_list(
    limit: int = 50,
    offset: int = 0,
    user_id: int | None = None,
    action: str | None = None,
    entity: str | None = None,
    entity_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    items, total = await list_audit_logs(
        db,
        limit=limit,
        offset=offset,
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
    )

    dto_items = [AuditLogResponse(**x).model_dump() for x in items]
    return {
        "ok": True,
        "result": AuditLogListResponse(items=[AuditLogResponse(**x) for x in items], total=total, limit=limit, offset=offset).model_dump(),
        "error": None,
    }
