from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user_any, get_db
from app.schemas.setting import SettingListResponse, SettingResponse, SettingUpsertRequest
from app.services.audit_log_service import write_audit_log
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


def _actor_payload(actor: Any) -> tuple[int | None, str]:
    actor_id = None
    if hasattr(actor, "id"):
        try:
            actor_id = int(getattr(actor, "id"))
        except Exception:
            actor_id = None

    actor_name = (
        getattr(actor, "username", None)
        or getattr(actor, "first_name", None)
        or "admin"
    )
    return actor_id, str(actor_name)


@router.get("", response_model=dict)
def admin_settings_list(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: Any = Depends(get_current_admin_user_any),
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
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    obj = upsert_setting(
        db,
        key=key,
        value=payload.value,
        description=getattr(payload, "description", None),
    )
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_SETTING_UPSERT",
        entity="setting",
        entity_id=None,
        data={
            "actor": actor_name,
            "key": key,
            "value": payload.value,
            "description": payload.description,
        },
    )
    dto = _to_schema(SettingResponse, obj)
    return {"ok": True, "result": _dump(dto), "error": None}


@router.delete("/{key}", response_model=dict)
def admin_settings_delete(
    key: str,
    db: Session = Depends(get_db),
    admin_actor: Any = Depends(get_current_admin_user_any),
):
    deleted = delete_setting(db, key=key)
    actor_id, actor_name = _actor_payload(admin_actor)
    write_audit_log(
        db,
        user_id=actor_id,
        action="ADMIN_SETTING_DELETE",
        entity="setting",
        entity_id=None,
        data={"actor": actor_name, "key": key, "deleted": deleted},
    )
    return {"ok": True, "result": {"deleted": deleted}, "error": None}
