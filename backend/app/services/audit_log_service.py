from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def write_audit_log(
    db: AsyncSession,
    *,
    user_id: Optional[int],
    action: str,
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
    data: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    commit: bool = True,
) -> None:
    data_json = None if data is None else json.dumps(data, ensure_ascii=False)

    await db.execute(
        text(
            """
            INSERT INTO audit_logs (user_id, action, entity, entity_id, data, ip, user_agent, created_at, updated_at)
            VALUES (:user_id, :action, :entity, :entity_id, COALESCE(:data, 'null')::jsonb, :ip, :user_agent, now(), now())
            """
        ),
        {
            "user_id": user_id,
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "data": data_json,
            "ip": ip,
            "user_agent": user_agent,
        },
    )

    if commit:
        await db.commit()


async def list_audit_logs(
    db: AsyncSession,
    *,
    limit: int,
    offset: int,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
) -> Tuple[List[dict], int]:
    where = []
    params = {"limit": limit, "offset": offset, "user_id": user_id, "action": action, "entity": entity, "entity_id": entity_id}

    if user_id is not None:
        where.append("user_id = :user_id")
    if action is not None:
        where.append("action = :action")
    if entity is not None:
        where.append("entity = :entity")
    if entity_id is not None:
        where.append("entity_id = :entity_id")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total = await db.scalar(
        text(f"SELECT COUNT(*) FROM audit_logs {where_sql}"),
        params,
    )

    rows = await db.execute(
        text(
            f"""
            SELECT id, user_id, action, created_at, entity, entity_id, data, ip, user_agent, updated_at
            FROM audit_logs
            {where_sql}
            ORDER BY id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )

    items = [dict(r._mapping) for r in rows.fetchall()]
    return items, int(total or 0)
