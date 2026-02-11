from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


def write_audit_log(
    db: Session,
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

    db.execute(
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
        db.commit()


def list_audit_logs(
    db: Session,
    *,
    limit: int,
    offset: int,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    training_id: Optional[int] = None,
) -> Tuple[List[dict], int]:
    where = []
    params = {
        "limit": limit,
        "offset": offset,
        "user_id": user_id,
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "date_from": date_from,
        "date_to": date_to,
        "training_id": training_id,
    }

    if user_id is not None:
        where.append("user_id = :user_id")
    if action is not None:
        where.append("action = :action")
    if entity is not None:
        where.append("entity = :entity")
    if entity_id is not None:
        where.append("entity_id = :entity_id")
    if date_from is not None:
        where.append("created_at >= :date_from")
    if date_to is not None:
        where.append("created_at <= :date_to")
    if training_id is not None:
        where.append(
            """
            (
                (entity = 'training' AND entity_id = :training_id)
                OR
                (data ? 'training_id' AND data->>'training_id' = CAST(:training_id AS text))
            )
            """
        )

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.execute(
        text(f"SELECT COUNT(*) FROM audit_logs {where_sql}"),
        params,
    ).scalar()

    rows = db.execute(
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
    ).mappings().all()

    items = [dict(r) for r in rows]
    return items, int(total or 0)
