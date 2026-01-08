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


@router.post("", response_model=dict)
def create_enrollment(
    payload: EnrollmentCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enrollment = enroll_user_to_training(
        db,
        user=user,
        training_id=payload.training_id,
        price_tier_id=getattr(payload, "price_tier_id", None),
    )
    return success_response(EnrollmentRead.model_validate(enrollment, from_attributes=True).model_dump())


@router.post("/{enrollment_id}/cancel", response_model=dict)
def cancel_my_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enrollment = cancel_enrollment_for_user(db, user=user, enrollment_id=enrollment_id)
    return success_response(EnrollmentRead.model_validate(enrollment, from_attributes=True).model_dump())


@router.get("/training/{training_id}", response_model=dict)
def roster(training_id: int, db: Session = Depends(get_db)):
    items = get_training_roster(db, training_id=training_id)
    return success_response([EnrollmentRead.model_validate(x, from_attributes=True).model_dump() for x in items])
