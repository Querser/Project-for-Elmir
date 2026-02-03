from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.deps import get_db

router = APIRouter(prefix="/locations", tags=["locations"])


def _pick_column(cols: set[str], candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in cols:
            return c
    return None


@router.get("")
def list_locations(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    only_with_trainings: bool = Query(True),
) -> dict[str, Any]:
    """
    Локации для фильтра тренировок:
    - id всегда
    - name/address — если такие колонки реально есть в таблице locations
    - latitude/longitude/maps_url — если есть в таблице (нужно для Яндекс.Карт)
    - only_with_trainings=True: возвращаем только локации, которые встречаются в trainings
    """

    insp = inspect(db.get_bind())
    loc_cols = {c["name"] for c in insp.get_columns("locations")}

    name_col = _pick_column(loc_cols, ["name", "title", "label"])
    address_col = _pick_column(loc_cols, ["address", "full_address", "addr", "location_address"])
    metro_col = _pick_column(loc_cols, ["metro", "subway", "station"])
    lat_col = _pick_column(loc_cols, ["latitude", "lat"])
    lon_col = _pick_column(loc_cols, ["longitude", "lon", "lng"])
    maps_url_col = _pick_column(loc_cols, ["maps_url", "map_url", "mapsUrl"])

    select_parts = ["l.id"]
    if name_col:
        select_parts.append(f"l.{name_col} AS name")
    if address_col:
        select_parts.append(f"l.{address_col} AS address")
    if metro_col:
        select_parts.append(f"l.{metro_col} AS metro")
    if lat_col:
        select_parts.append(f"l.{lat_col} AS latitude")
    if lon_col:
        select_parts.append(f"l.{lon_col} AS longitude")
    if maps_url_col:
        select_parts.append(f"l.{maps_url_col} AS maps_url")

    join_sql = "JOIN trainings t ON t.location_id = l.id" if only_with_trainings else ""

    order_parts = []
    if name_col:
        order_parts.append("name")
    if address_col:
        order_parts.append("address")
    if metro_col:
        order_parts.append("metro")
    order_parts.append("l.id")
    order_sql = ", ".join(order_parts)

    base_sql = f"""
        FROM locations l
        {join_sql}
    """

    list_sql = f"""
        SELECT DISTINCT {", ".join(select_parts)}
        {base_sql}
        ORDER BY {order_sql}
        LIMIT :limit OFFSET :offset
    """

    count_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT l.id
            {base_sql}
        ) AS q
    """

    rows = db.execute(text(list_sql), {"limit": limit, "offset": offset}).mappings().all()
    total = int(db.execute(text(count_sql)).scalar() or 0)

    items: list[dict[str, Any]] = []
    for r in rows:
        item = {"id": r["id"]}
        if "name" in r:
            item["name"] = r["name"]
        if "address" in r:
            item["address"] = r["address"]
        if "metro" in r:
            item["metro"] = r["metro"]
        if "latitude" in r:
            item["latitude"] = r["latitude"]
        if "longitude" in r:
            item["longitude"] = r["longitude"]
        if "maps_url" in r:
            item["maps_url"] = r["maps_url"]
        items.append(item)

    return {"items": items, "total": total, "limit": limit, "offset": offset}