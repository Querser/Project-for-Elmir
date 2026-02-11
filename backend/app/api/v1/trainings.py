from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user_any, get_current_user_optional, get_db
from app.core.exceptions import AppException
from app.schemas.training import TrainingCreate, TrainingUpdate
from app.schemas.training_ui import TrainingReadUI, TrainingsPageUI
from app.services.training_service import (
    cancel_training,
    create_training,
    delete_training,
    get_training_or_404,
    list_trainings,
    restore_training,
    update_training,
)
from app.services.training_integration_service import (
    build_training_calendar_payload,
    build_training_ics_content,
    build_yandex_map_payload,
)
from app.services.training_ui_service import build_training_ui_payload

router = APIRouter(prefix='/trainings', tags=['trainings'])

_ALLOWED_MEDIA_PREFIXES = ('image/', 'video/')
_MAX_MEDIA_BYTES = 50 * 1024 * 1024
_MEDIA_ROOT = Path(__file__).resolve().parents[3] / 'media' / 'trainings'


def _normalize_json(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, datetime):
        return v
    if isinstance(v, list):
        return [_normalize_json(x) for x in v]
    if isinstance(v, tuple):
        return [_normalize_json(x) for x in v]
    if isinstance(v, dict):
        return {k: _normalize_json(val) for k, val in v.items()}
    return v


def _price_tier_to_dict(pt: Any) -> dict[str, Any]:
    return {
        'id': getattr(pt, 'id', None),
        'training_id': getattr(pt, 'training_id', None),
        'title': getattr(pt, 'title', ''),
        'price': _normalize_json(getattr(pt, 'price', None)),
        'sort_order': getattr(pt, 'sort_order', 0),
        'level_id': getattr(pt, 'level_id', None),
    }


def _training_to_dict(t: Any) -> dict[str, Any]:
    pts = getattr(t, 'price_tiers', []) or []
    pts_dict = [_price_tier_to_dict(x) for x in pts]
    pts_dict.sort(key=lambda x: (x.get('sort_order') or 0, x.get('id') or 0))

    location_obj = getattr(t, 'location', None)
    location_name = None
    location_payload: dict[str, Any] | None = None
    if location_obj is not None and not isinstance(location_obj, str):
        location_payload = {
            'id': getattr(location_obj, 'id', None),
            'name': getattr(location_obj, 'name', None),
            'address': getattr(location_obj, 'address', None),
            'latitude': getattr(location_obj, 'latitude', None),
            'longitude': getattr(location_obj, 'longitude', None),
            'maps_url': getattr(location_obj, 'maps_url', None),
        }
        location_name = location_payload.get('name') or location_payload.get('address')

    return {
        'id': getattr(t, 'id', None),
        'title': getattr(t, 'title', ''),
        'description': getattr(t, 'description', None),
        'start_at': getattr(t, 'start_at', None),
        'duration_minutes': getattr(t, 'duration_minutes', None),
        'min_level_name': getattr(t, 'min_level_name', None),
        'max_level_name': getattr(t, 'max_level_name', None),
        'price': _normalize_json(getattr(t, 'price', None)),
        'capacity_main': getattr(t, 'capacity_main', None),
        'capacity_reserve': getattr(t, 'capacity_reserve', None),
        'coach_name': getattr(t, 'coach_name', None),
        'image_url': getattr(t, 'image_url', None),
        'video_url': getattr(t, 'video_url', None),
        'location_id': getattr(t, 'location_id', None),
        'location_name': location_name,
        'location': location_name,
        'location_info': location_payload,
        'address': location_payload.get('address') if location_payload else None,
        'is_cancelled': bool(getattr(t, 'is_cancelled', False)),
        'price_tiers': pts_dict,
    }


def _to_training_read_ui_payload(
    db: Session,
    training_obj: Any,
    user: Any | None,
    *,
    request: Request | None = None,
    include_participants: bool = False,
) -> dict[str, Any]:
    base = _normalize_json(_training_to_dict(training_obj))
    ui = _normalize_json(build_training_ui_payload(db, training_obj, user, include_participants=include_participants))
    base.update(ui)

    base_api_url = ""
    if request is not None:
        base_api_url = str(request.base_url).rstrip("/")

    maps_payload = _normalize_json(build_yandex_map_payload(training_obj))
    calendar_payload = _normalize_json(
        build_training_calendar_payload(training_obj, base_api_url=base_api_url)
    )

    base["maps"] = maps_payload
    base["calendar"] = calendar_payload
    base["yandex_route_url"] = (maps_payload or {}).get("route_url")
    base["yandex_map_url"] = (maps_payload or {}).get("open_url")
    base["calendar_google_url"] = (calendar_payload or {}).get("google_url")
    base["calendar_ics_url"] = (calendar_payload or {}).get("ics_url")

    return base


def _safe_extension(upload: UploadFile) -> str:
    filename = (upload.filename or '').strip()
    suffix = Path(filename).suffix.lower()
    if suffix and len(suffix) <= 10 and suffix.replace('.', '').isalnum():
        return suffix

    content_type = (upload.content_type or '').lower()
    if content_type == 'image/jpeg':
        return '.jpg'
    if content_type == 'image/png':
        return '.png'
    if content_type == 'image/webp':
        return '.webp'
    if content_type == 'video/mp4':
        return '.mp4'
    if content_type == 'video/webm':
        return '.webm'
    return '.bin'


@router.get('/admin', response_model=TrainingsPageUI)
def list_admin_trainings(
    request: Request,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user_any),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    q: str | None = Query(None, max_length=200),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    location_id: int | None = Query(None),
    coach_name: str | None = Query(None, max_length=100),
    min_level_name: str | None = Query(None, max_length=50),
    max_level_name: str | None = Query(None, max_length=50),
    is_cancelled: bool | None = Query(None),
    order: str = Query('asc', pattern='^(asc|desc)$'),
):
    items, total = list_trainings(
        db,
        q=q,
        date_from=date_from,
        date_to=date_to,
        location_id=location_id,
        coach_name=coach_name,
        min_level_name=min_level_name,
        max_level_name=max_level_name,
        include_cancelled=True,
        is_cancelled=is_cancelled,
        order=order,
        limit=limit,
        offset=skip,
    )
    payload = [
        _to_training_read_ui_payload(db, t, None, request=request, include_participants=False)
        for t in (items or [])
    ]
    return {'items': payload, 'total': total, 'limit': limit, 'offset': skip}


@router.get('/admin/{training_id}', response_model=TrainingReadUI)
def get_admin_training(
    training_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user_any),
):
    training = get_training_or_404(db=db, training_id=training_id)
    return _to_training_read_ui_payload(db, training, None, request=request, include_participants=True)


@router.post('/media', response_model=dict)
async def upload_training_media(
    file: UploadFile = File(...),
    _: Any = Depends(get_current_admin_user_any),
):
    content_type = (file.content_type or '').lower().strip()
    if not any(content_type.startswith(prefix) for prefix in _ALLOWED_MEDIA_PREFIXES):
        raise AppException.validation('Разрешены только image/* и video/* файлы')

    data = await file.read()
    if not data:
        raise AppException.validation('Файл пустой')
    if len(data) > _MAX_MEDIA_BYTES:
        raise AppException.validation('Файл слишком большой (максимум 50 МБ)')

    _MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    ext = _safe_extension(file)
    filename = f"{uuid4().hex}{ext}"
    destination = _MEDIA_ROOT / filename
    destination.write_bytes(data)

    return {
        'ok': True,
        'result': {
            'url': f'/media/trainings/{filename}',
            'content_type': content_type,
            'size': len(data),
            'filename': filename,
        },
    }


@router.post('', response_model=TrainingReadUI)
def create_training_admin(
    payload: TrainingCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user_any),
):
    created = create_training(db=db, data=payload)
    return _to_training_read_ui_payload(db, created, None, request=request, include_participants=True)


@router.patch('/{training_id}', response_model=TrainingReadUI)
def update_training_admin(
    training_id: int,
    payload: TrainingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user_any),
):
    training = get_training_or_404(db=db, training_id=training_id)
    updated = update_training(db=db, training=training, data=payload)
    return _to_training_read_ui_payload(db, updated, None, request=request, include_participants=True)


@router.delete('/{training_id}', response_model=dict)
def delete_training_admin(
    training_id: int,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user_any),
):
    training = get_training_or_404(db=db, training_id=training_id)
    delete_training(db=db, training=training)
    return {'ok': True}


@router.post('/{training_id}/cancel', response_model=TrainingReadUI)
def cancel_training_admin(
    training_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user_any),
):
    training = get_training_or_404(db=db, training_id=training_id)
    cancelled = cancel_training(db=db, training=training)
    return _to_training_read_ui_payload(db, cancelled, None, request=request, include_participants=True)


@router.post('/{training_id}/restore', response_model=TrainingReadUI)
def restore_training_admin(
    training_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_admin_user_any),
):
    training = get_training_or_404(db=db, training_id=training_id)
    restored = restore_training(db=db, training=training)
    return _to_training_read_ui_payload(db, restored, None, request=request, include_participants=True)


@router.get('', response_model=TrainingsPageUI)
def list_public_trainings(
    request: Request,
    db: Session = Depends(get_db),
    user: Any | None = Depends(get_current_user_optional),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    now_utc = datetime.now(timezone.utc)

    items, total = list_trainings(
        db,
        date_from=now_utc,
        include_cancelled=False,
        order='asc',
        limit=limit,
        offset=skip,
    )

    payload = [
        _to_training_read_ui_payload(db, t, user, request=request, include_participants=False)
        for t in (items or [])
    ]
    return {'items': payload, 'total': total, 'limit': limit, 'offset': skip}


@router.get('/{training_id}/calendar.ics')
def get_training_calendar_ics(
    training_id: int,
    db: Session = Depends(get_db),
):
    training = get_training_or_404(db=db, training_id=training_id)
    content = build_training_ics_content(training)
    filename = f"training-{training_id}.ics"
    return Response(
        content=content,
        media_type='text/calendar; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Cache-Control': 'no-store',
        },
    )


@router.get('/{training_id}', response_model=TrainingReadUI)
def get_public_training(
    training_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Any | None = Depends(get_current_user_optional),
):
    training = get_training_or_404(db=db, training_id=training_id)

    if bool(getattr(training, 'is_cancelled', False)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Training not found')

    return _to_training_read_ui_payload(db, training, user, request=request, include_participants=True)
