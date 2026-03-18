from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.responses import success_response
from app.models.user import User
from app.schemas.enrollment import EnrollmentCreateRequest, EnrollmentRead
from app.services.enrollment_service import (
    enroll_user_to_training,
    cancel_enrollment_for_user,
    get_training_roster,
)

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


def _unexpected_kwarg(err: TypeError, kw: str) -> bool:
    """
    Ловим ТОЛЬКО несовпадение сигнатуры (unexpected keyword argument).

    Python формирует сообщение примерно так:
      - "enroll_user_to_training() got an unexpected keyword argument 'user'"
    """
    msg = str(err)
    return "unexpected keyword argument" in msg and f"'{kw}'" in msg


def _call_enroll_service(db: Session, user: User, payload: EnrollmentCreateRequest):
    """
    Поддерживаем несколько возможных сигнатур сервиса:
      1) enroll_user_to_training(db, user_id=..., training_id=..., ...)
      2) enroll_user_to_training(db, user=..., training_id=..., ...)
      3) enroll_user_to_training(db, telegram_id=..., training_id=..., ...)

    В твоей кодовой базе чаще всего используется (1).
    """
    base_kwargs = {
        "training_id": payload.training_id,
        "price_tier_id": getattr(payload, "price_tier_id", None),
        "is_paid": getattr(payload, "is_paid", False),
        "position_key": getattr(payload, "position_key", None),
    }

    # 1) user_id=... (наиболее вероятно/правильно для твоего проекта)
    try:
        return enroll_user_to_training(db, user_id=user.id, **base_kwargs)
    except TypeError as e:
        # если ошибка НЕ про keyword user_id — пробрасываем (это реальная ошибка внутри сервиса)
        if not _unexpected_kwarg(e, "user_id"):
            raise

    # 2) user=...
    try:
        return enroll_user_to_training(db, user=user, **base_kwargs)
    except TypeError as e:
        if not _unexpected_kwarg(e, "user"):
            raise

    # 3) telegram_id=... (если модель User реально содержит telegram_id)
    telegram_id = getattr(user, "telegram_id", None)
    if telegram_id is not None:
        try:
            return enroll_user_to_training(db, telegram_id=telegram_id, **base_kwargs)
        except TypeError as e:
            if not _unexpected_kwarg(e, "telegram_id"):
                raise

    # Если дошли сюда — сигнатура сервиса другая (или переименованы аргументы)
    raise TypeError(
        "enroll_user_to_training: unsupported signature. "
        "Expected one of: user_id= / user= / telegram_id= plus training_id."
    )


def _call_cancel_service(db: Session, user: User, enrollment_id: int):
    """
    Поддерживаем несколько возможных сигнатур:
      1) cancel_enrollment_for_user(db, user_id=..., enrollment_id=...)  (или id=...)
      2) cancel_enrollment_for_user(db, user=..., enrollment_id=...)     (или id=...)
      3) cancel_enrollment_for_user(db, telegram_id=..., enrollment_id=...) (или id=...)

    В твоей кодовой базе чаще всего используется (1).
    """

    # 1) user_id=... (сначала enrollment_id=..., потом fallback id=...)
    try:
        return cancel_enrollment_for_user(db, user_id=user.id, enrollment_id=enrollment_id)
    except TypeError as e:
        if _unexpected_kwarg(e, "enrollment_id"):
            # пробуем id=
            try:
                return cancel_enrollment_for_user(db, user_id=user.id, id=enrollment_id)
            except TypeError as e2:
                # если это НЕ про keyword — пробрасываем
                if not (_unexpected_kwarg(e2, "user_id") or _unexpected_kwarg(e2, "id")):
                    raise
        elif not _unexpected_kwarg(e, "user_id"):
            raise

    # 2) user=... (сначала enrollment_id=..., потом fallback id=...)
    try:
        return cancel_enrollment_for_user(db, user=user, enrollment_id=enrollment_id)
    except TypeError as e:
        if _unexpected_kwarg(e, "enrollment_id"):
            try:
                return cancel_enrollment_for_user(db, user=user, id=enrollment_id)
            except TypeError as e2:
                if not (_unexpected_kwarg(e2, "user") or _unexpected_kwarg(e2, "id")):
                    raise
        elif not _unexpected_kwarg(e, "user"):
            raise

    # 3) telegram_id=... (если доступен)
    telegram_id = getattr(user, "telegram_id", None)
    if telegram_id is not None:
        try:
            return cancel_enrollment_for_user(db, telegram_id=telegram_id, enrollment_id=enrollment_id)
        except TypeError as e:
            if _unexpected_kwarg(e, "enrollment_id"):
                try:
                    return cancel_enrollment_for_user(db, telegram_id=telegram_id, id=enrollment_id)
                except TypeError as e2:
                    if not (_unexpected_kwarg(e2, "telegram_id") or _unexpected_kwarg(e2, "id")):
                        raise
            elif not _unexpected_kwarg(e, "telegram_id"):
                raise

    raise TypeError(
        "cancel_enrollment_for_user: unsupported signature. "
        "Expected one of: user_id= / user= / telegram_id= plus enrollment_id (or id)."
    )


@router.post("", response_model=dict)
def create_enrollment(
    payload: EnrollmentCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enrollment = _call_enroll_service(db=db, user=user, payload=payload)
    return success_response(
        EnrollmentRead.model_validate(enrollment, from_attributes=True).model_dump()
    )


@router.post("/{enrollment_id}/cancel", response_model=dict)
def cancel_my_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enrollment = _call_cancel_service(db=db, user=user, enrollment_id=enrollment_id)
    return success_response(
        EnrollmentRead.model_validate(enrollment, from_attributes=True).model_dump()
    )


@router.get("/training/{training_id}", response_model=dict)
def roster(training_id: int, db: Session = Depends(get_db)):
    items = get_training_roster(db, training_id=training_id)
    return success_response(
        [EnrollmentRead.model_validate(x, from_attributes=True).model_dump() for x in items]
    )
