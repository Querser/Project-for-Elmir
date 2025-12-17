# app/api/v1/enrollments.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.middleware import get_current_user
from app.core.responses import success_response
from app.db.session import get_db
from app.models.user import User
from app.schemas.enrollment import (
    EnrollmentCreateRequest,
    EnrollmentResponse,
)
from app.services.enrollment_service import (
    enroll_user_to_training,
    cancel_enrollment_for_user,
    get_training_roster,
)

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.post("")
async def enroll_to_training(
    data: EnrollmentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    POST /api/v1/enrollments
    Записаться на тренировку.
    """
    enrollment = enroll_user_to_training(
        db,
        user=current_user,
        training_id=data.training_id,
    )
    dto = EnrollmentResponse.model_validate(enrollment, from_attributes=True)
    return success_response(dto.model_dump())


@router.post("/{enrollment_id}/cancel")
async def cancel_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    POST /api/v1/enrollments/{id}/cancel
    Отменить свою запись.
    """
    enrollment = cancel_enrollment_for_user(
        db,
        user=current_user,
        enrollment_id=enrollment_id,
    )
    dto = EnrollmentResponse.model_validate(enrollment, from_attributes=True)
    return success_response(dto.model_dump())


@router.get("/training/{training_id}")
async def get_training_enrollments(
    training_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    GET /api/v1/enrollments/training/{training_id}
    Получить состав тренировки (основа и резерв).
    """
    main, reserve = get_training_roster(db, training_id)

    main_dtos = [
        EnrollmentResponse.model_validate(e, from_attributes=True).model_dump()
        for e in main
    ]
    reserve_dtos = [
        EnrollmentResponse.model_validate(e, from_attributes=True).model_dump()
        for e in reserve
    ]

    return success_response(
        {
            "training_id": training_id,
            "main": main_dtos,
            "reserve": reserve_dtos,
        }
    )
