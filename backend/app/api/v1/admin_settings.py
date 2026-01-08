from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db

# В разных ветках проекта могло называться по-разному
try:
    from app.core.deps import require_admin
except ImportError:  # fallback
    from app.core.deps import get_current_admin_user as require_admin  # type: ignore

# ВАЖНО: эти схемы должны реально существовать в app/schemas/setting.py
# (у тебя раньше именно так и было, а SettingCreateRequest — нет)
from app.schemas.setting import SettingListResponse, SettingResponse, SettingUpsertRequest
from app.services.setting_service import delete_setting, list_settings, upsert_setting

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


def _to_schema(cls, obj):
    if hasattr(cls, "model_validate"):
        return cls.model_validate(obj, from_attributes=True)
    if hasattr(cls, "from_orm"):
        return cls.from_orm(obj)
    return cls(**obj)


def _dump(model):
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


@router.get("", response_model=dict)
def admin_settings_list(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: Any = Depends(require_admin),
):
    items, total = list_settings(db, limit=limit, offset=offset)
    dto_items = [_to_schema(SettingResponse, x) for x in items]
    result = SettingListResponse(items=dto_items, total=total, limit=limit, offset=offset)
    return {"ok": True, "result": _dump(result), "error": None}


@router.put("/{key}", response_model=dict)
def admin_settings_upsert(
    key: str,
    payload: SettingUpsertRequest,
    db: Session = Depends(get_db),
    _admin: Any = Depends(require_admin),
):
    obj = upsert_setting(db, key=key, value=payload.value, description=getattr(payload, "description", None))
    dto = _to_schema(SettingResponse, obj)
    return {"ok": True, "result": _dump(dto), "error": None}


@router.delete("/{key}", response_model=dict)
def admin_settings_delete(
    key: str,
    db: Session = Depends(get_db),
    _admin: Any = Depends(require_admin),
):
    deleted = delete_setting(db, key=key)
    return {"ok": True, "result": {"deleted": deleted}, "error": None}
