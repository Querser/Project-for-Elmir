from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin
from app.schemas.setting import SettingListResponse, SettingResponse, SettingUpsertRequest
from app.services.audit_log_service import write_audit_log
from app.services.setting_service import delete_setting, get_setting, list_settings, upsert_setting

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


@router.get("", response_model=dict)
async def admin_settings_list(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    items, total = await list_settings(db, limit=limit, offset=offset)
    return {
        "ok": True,
        "result": SettingListResponse(
            items=[SettingResponse.model_validate(x) for x in items],
            total=total,
            limit=limit,
            offset=offset,
        ).model_dump(),
        "error": None,
    }


@router.get("/{key}", response_model=dict)
async def admin_settings_get(
    key: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    s = await get_setting(db, key=key)
    if s is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"ok": True, "result": SettingResponse.model_validate(s).model_dump(), "error": None}


@router.post("", response_model=dict)
async def admin_settings_upsert(
    payload: SettingUpsertRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    s = await upsert_setting(db, key=payload.key, value=payload.value, description=payload.description)

    await write_audit_log(
        db,
        user_id=getattr(admin, "id", None),
        action="ADMIN_SETTING_UPSERT",
        entity="setting",
        entity_id=None,
        data={"key": payload.key, "value": payload.value, "description": payload.description},
        commit=True,
    )

    return {"ok": True, "result": SettingResponse.model_validate(s).model_dump(), "error": None}


@router.delete("/{key}", response_model=dict)
async def admin_settings_delete(
    key: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    ok = await delete_setting(db, key=key)

    await write_audit_log(
        db,
        user_id=getattr(admin, "id", None),
        action="ADMIN_SETTING_DELETE",
        entity="setting",
        entity_id=None,
        data={"key": key, "deleted": ok},
        commit=True,
    )

    return {"ok": True, "result": ok, "error": None}
