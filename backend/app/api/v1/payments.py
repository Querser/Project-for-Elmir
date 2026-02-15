from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.exceptions import AppException, ErrorCode
from app.core.responses import success_response
from app.models.enrollment import Enrollment
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.services.enrollment_service import enroll_user_to_training
from app.services.payment_retention_service import purge_payments_older_than_quarter
from app.services.training_service import get_training_or_404
from app.services.training_ui_service import build_training_ui_payload
from app.services.yookassa_service import (
    create_redirect_payment,
    get_payment,
    get_return_url_default,
    payments_enabled,
)

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)


class EnrollmentCheckoutRequest(BaseModel):
    training_id: int
    price_tier_id: int | None = None
    return_url: str | None = Field(default=None, max_length=2000)


def _run_payments_retention_cleanup(db: Session) -> None:
    try:
        deleted = purge_payments_older_than_quarter(db)
        if deleted:
            logger.info("Payments retention cleanup removed %s old rows", deleted)
    except Exception:
        logger.exception("Payments retention cleanup failed")


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _append_query_params(url: str, params: dict[str, Any]) -> str:
    base = str(url or "").strip()
    if not base:
        return ""

    try:
        parts = urlsplit(base)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        for key, value in params.items():
            if value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            query[str(key)] = text
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    except Exception:
        return base


def _build_return_url(
    db: Session,
    *,
    request: Request,
    payload_return_url: str | None,
    training_id: int,
    telegram_id: int | None,
) -> str:
    raw = str(payload_return_url or "").strip()
    if not raw:
        raw = get_return_url_default(db)
    if not raw:
        raw = str(request.base_url).rstrip("/")
    if not raw:
        raise AppException.validation(message="Не удалось определить return_url для ЮKassa")

    return _append_query_params(
        raw,
        {
            "training_id": training_id,
            "tg_id": telegram_id,
            "payment_result": "1",
        },
    )


def _as_amount(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise AppException.validation(message="Некорректная сумма платежа")
    if amount <= Decimal("0"):
        raise AppException.validation(message="Сумма платежа должна быть больше 0")
    return amount.quantize(Decimal("0.01"))


def _status_str(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value)).strip().lower()


def _resolve_checkout_context(db: Session, *, user: User, training_id: int) -> dict[str, Any]:
    training = get_training_or_404(db=db, training_id=training_id)
    if bool(getattr(training, "is_cancelled", False)):
        raise AppException.conflict(
            code=ErrorCode.TRAINING_CANCELLED,
            message="Тренировка отменена",
            details={"training_id": training_id},
        )

    ui_payload = build_training_ui_payload(db, training, user, include_participants=False)
    user_enrollment_status = _status_str(ui_payload.get("user_enrollment_status"))
    if user_enrollment_status in {"main", "reserve"}:
        raise AppException.conflict(
            code=ErrorCode.ALREADY_ENROLLED,
            message="Вы уже записаны на эту тренировку",
            details={"training_id": training_id},
        )

    if bool(ui_payload.get("user_has_active_ban")):
        reason = str(ui_payload.get("user_active_ban_reason") or ui_payload.get("user_active_ban_text") or "").strip()
        raise AppException.forbidden(
            message=reason or "Запись недоступна: у вас активный бан",
            details={"training_id": training_id},
        )

    level_block_reason = str(ui_payload.get("user_level_block_reason") or "").strip()
    if level_block_reason:
        raise AppException.forbidden(
            message=level_block_reason,
            details={"training_id": training_id},
        )

    can_enroll = bool(ui_payload.get("can_enroll"))
    can_enroll_reserve = bool(ui_payload.get("can_enroll_reserve"))
    if not (can_enroll or can_enroll_reserve):
        raise AppException.conflict(
            code=ErrorCode.TRAINING_FULL,
            message="На тренировку больше нет свободных мест",
            details={"training_id": training_id},
        )

    amount = _as_amount(ui_payload.get("final_price") or ui_payload.get("price") or 0)
    picked_price_tier_id = _safe_int(ui_payload.get("picked_price_tier_id"))

    return {
        "training": training,
        "amount": amount,
        "picked_price_tier_id": picked_price_tier_id,
        "ui_payload": ui_payload,
    }


def _payment_status_to_local(provider_status: str) -> PaymentStatus:
    normalized = str(provider_status or "").strip().lower()
    if normalized == "succeeded":
        return PaymentStatus.PAID
    if normalized == "canceled":
        return PaymentStatus.FAILED
    if normalized == "refunded":
        return PaymentStatus.REFUNDED
    return PaymentStatus.PENDING


@router.post("/enrollments/checkout", response_model=dict)
def create_enrollment_checkout(
    payload: EnrollmentCheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not payments_enabled(db):
        raise AppException.conflict(message="Прием оплат временно отключен")

    _run_payments_retention_cleanup(db)

    checkout = _resolve_checkout_context(db, user=user, training_id=payload.training_id)
    training = checkout["training"]
    amount: Decimal = checkout["amount"]
    picked_price_tier_id = checkout["picked_price_tier_id"]

    if payload.price_tier_id is not None and picked_price_tier_id is not None:
        if int(payload.price_tier_id) != int(picked_price_tier_id):
            raise AppException.validation(
                message="Выбранный тариф не соответствует уровню игрока",
                details={
                    "expected_price_tier_id": picked_price_tier_id,
                    "provided_price_tier_id": payload.price_tier_id,
                },
            )

    return_url = _build_return_url(
        db,
        request=request,
        payload_return_url=payload.return_url,
        training_id=int(training.id),
        telegram_id=_safe_int(getattr(user, "telegram_id", None)),
    )

    metadata = {
        "user_id": str(user.id),
        "training_id": str(training.id),
        "price_tier_id": str(picked_price_tier_id) if picked_price_tier_id is not None else "",
    }
    description = f"Тренировка #{training.id}: {str(getattr(training, 'title', '') or '').strip()}"

    provider_payment = create_redirect_payment(
        db,
        amount_rub=amount,
        description=description,
        return_url=return_url,
        metadata=metadata,
    )

    provider_payment_id = str(provider_payment.get("id") or "").strip()
    confirmation_url = str(((provider_payment.get("confirmation") or {}).get("confirmation_url")) or "").strip()
    provider_status = str(provider_payment.get("status") or "").strip().lower()

    if not provider_payment_id or not confirmation_url:
        raise AppException.conflict(
            message="ЮKassa не вернула ссылку на оплату",
            details={"provider_payment": provider_payment},
        )

    local_payment = Payment(
        user_id=int(user.id),
        training_id=int(training.id),
        amount=float(amount),
        currency="RUB",
        status=_payment_status_to_local(provider_status),
        provider_payment_id=provider_payment_id,
    )
    db.add(local_payment)
    db.commit()
    db.refresh(local_payment)

    return success_response(
        {
            "payment_id": provider_payment_id,
            "confirmation_url": confirmation_url,
            "status": provider_status or "pending",
            "amount": f"{amount:.2f}",
            "currency": "RUB",
            "training_id": int(training.id),
            "price_tier_id": picked_price_tier_id,
            "local_payment_id": int(local_payment.id),
        }
    )


@router.get("/enrollments/{provider_payment_id}/status", response_model=dict)
def get_enrollment_payment_status(
    provider_payment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _run_payments_retention_cleanup(db)

    payment_id = str(provider_payment_id or "").strip()
    if not payment_id:
        raise AppException.validation(message="Некорректный payment_id")

    local_payment = (
        db.query(Payment)
        .filter(Payment.provider_payment_id == payment_id, Payment.user_id == int(user.id))
        .one_or_none()
    )
    if local_payment is None:
        raise AppException.not_found(
            code=ErrorCode.PAYMENT_NOT_FOUND,
            message="Платеж не найден",
            details={"payment_id": payment_id},
        )

    provider_payment = get_payment(db, provider_payment_id=payment_id)
    provider_status = str(provider_payment.get("status") or "").strip().lower()
    local_status = _payment_status_to_local(provider_status)

    if local_payment.status != local_status:
        local_payment.status = local_status
        db.add(local_payment)

    enrollment_payload: dict[str, Any] = {
        "created_or_updated": False,
        "enrollment_id": None,
        "status": None,
        "error": None,
    }

    if local_status == PaymentStatus.PAID:
        if local_payment.paid_at is None:
            local_payment.paid_at = datetime.now(timezone.utc)
            db.add(local_payment)

        metadata = provider_payment.get("metadata") or {}
        training_id = _safe_int(getattr(local_payment, "training_id", None)) or _safe_int(metadata.get("training_id"))
        price_tier_id = _safe_int(metadata.get("price_tier_id"))

        if training_id is not None:
            try:
                enrollment = enroll_user_to_training(
                    db,
                    training_id=int(training_id),
                    user_id=int(user.id),
                    is_paid=True,
                    price_tier_id=price_tier_id,
                )
                enrollment_payload = {
                    "created_or_updated": True,
                    "enrollment_id": int(getattr(enrollment, "id")),
                    "status": _status_str(getattr(enrollment, "status", None)),
                    "error": None,
                }
            except AppException as exc:
                # Already enrolled is safe: just mark enrollment as paid.
                if str(exc.code) == ErrorCode.ALREADY_ENROLLED.value:
                    existing = (
                        db.query(Enrollment)
                        .filter(Enrollment.user_id == int(user.id), Enrollment.training_id == int(training_id))
                        .one_or_none()
                    )
                    if existing is not None:
                        if hasattr(existing, "is_paid") and not bool(getattr(existing, "is_paid", False)):
                            existing.is_paid = True
                            db.add(existing)
                        enrollment_payload = {
                            "created_or_updated": True,
                            "enrollment_id": int(getattr(existing, "id")),
                            "status": _status_str(getattr(existing, "status", None)),
                            "error": None,
                        }
                    else:
                        enrollment_payload["error"] = exc.message
                else:
                    enrollment_payload["error"] = exc.message

    db.commit()
    db.refresh(local_payment)

    cancellation_details = provider_payment.get("cancellation_details") or {}
    amount_obj = provider_payment.get("amount") or {}

    return success_response(
        {
            "payment_id": payment_id,
            "status": provider_status or "pending",
            "local_status": _status_str(local_payment.status),
            "amount": str(amount_obj.get("value") or local_payment.amount),
            "currency": str(amount_obj.get("currency") or local_payment.currency or "RUB"),
            "confirmation_url": ((provider_payment.get("confirmation") or {}).get("confirmation_url")),
            "cancellation_reason": cancellation_details.get("reason"),
            "enrollment": enrollment_payload,
        }
    )
