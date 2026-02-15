from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional


CANCEL_DEADLINE_HOURS = 2

# Автобан: если есть открытые долги старше этого времени — баним (можешь подкрутить)
AUTOBAN_DEBT_GRACE_HOURS = 24
AUTOBAN_DEFAULT_BAN_DAYS = 30

# Отмена со штрафом, если до старта меньше N часов
CANCEL_HOURS_BEFORE_TRAINING = 2
# Через сколько дней AutoBanJob банит за неоплаченный debt
AUTOBAN_DEBT_AGE_DAYS = 7


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_training_start_at(training: Any) -> Optional[datetime]:
    """
    В проекте исторически встречаются разные имена: start_at / starts_at.
    Берём то, что реально есть.
    """
    dt = getattr(training, "start_at", None)
    if dt is None:
        dt = getattr(training, "starts_at", None)
    return dt


def cancel_deadline_at(training: Any, *, cancel_hours: Optional[int] = None) -> Optional[datetime]:
    start = get_training_start_at(training)
    if start is None:
        return None
    hours = CANCEL_DEADLINE_HOURS if cancel_hours is None else int(cancel_hours)
    if hours < 0:
        hours = 0
    return start - timedelta(hours=hours)


def is_late_cancel(
    training: Any,
    *,
    now: Optional[datetime] = None,
    cancel_hours: Optional[int] = None,
) -> bool:
    now = now or utcnow()
    deadline = cancel_deadline_at(training, cancel_hours=cancel_hours)
    if deadline is None:
        # если у тренировки нет start_at — считаем, что “не поздно” (не штрафуем)
        return False
    return now > deadline


@dataclass(frozen=True)
class PricePick:
    final_price: Decimal
    price_min: Decimal
    price_max: Decimal
    picked_tier_id: Optional[int]


def _as_decimal(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def pick_price_for_user(
    training: Any,
    user: Any | None,
    price_tiers: Iterable[Any] | None,
) -> PricePick:
    """
    Универсальный выбор цены:
    - если есть price tiers:
        - min/max = по ним
        - final_price = “лучший” для пользователя:
            1) точное совпадение по level_id (если такие поля есть)
            2) tier без level_id (дефолтный)
            3) самый дешёвый
    - иначе final_price = training.price
    """
    base_price = _as_decimal(getattr(training, "price", None) or 0)

    tiers = list(price_tiers or [])
    if not tiers:
        return PricePick(final_price=base_price, price_min=base_price, price_max=base_price, picked_tier_id=None)

    tier_prices = [_as_decimal(getattr(t, "price", None) or 0) for t in tiers]
    price_min = min(tier_prices) if tier_prices else base_price
    price_max = max(tier_prices) if tier_prices else base_price

    user_level_id = getattr(user, "level_id", None) if user is not None else None

    # 1) match level_id
    if user_level_id is not None:
        for t in tiers:
            if getattr(t, "level_id", None) == user_level_id:
                return PricePick(
                    final_price=_as_decimal(getattr(t, "price", None) or base_price),
                    price_min=price_min,
                    price_max=price_max,
                    picked_tier_id=getattr(t, "id", None),
                )

    # 2) default tier without level_id
    for t in tiers:
        if getattr(t, "level_id", None) is None:
            return PricePick(
                final_price=_as_decimal(getattr(t, "price", None) or base_price),
                price_min=price_min,
                price_max=price_max,
                picked_tier_id=getattr(t, "id", None),
            )

    # 3) cheapest
    cheapest = min(tiers, key=lambda t: _as_decimal(getattr(t, "price", None) or 0))
    return PricePick(
        final_price=_as_decimal(getattr(cheapest, "price", None) or base_price),
        price_min=price_min,
        price_max=price_max,
        picked_tier_id=getattr(cheapest, "id", None),
    )
