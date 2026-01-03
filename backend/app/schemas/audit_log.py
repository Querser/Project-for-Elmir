from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    created_at: datetime

    entity: Optional[str] = None
    entity_id: Optional[int] = None
    data: Optional[Dict[str, Any]] = None

    ip: Optional[str] = None
    user_agent: Optional[str] = None
    updated_at: Optional[datetime] = None


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    limit: int
    offset: int
