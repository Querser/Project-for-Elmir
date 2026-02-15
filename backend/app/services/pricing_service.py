from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.models.level import Level
from app.models.price_tier import PriceTier
from app.models.training import Training
from app.models.user import User


def list_price_tiers(db: Session, training_id: int) -> list[PriceTier]:
    return (
        db.query(PriceTier)
        .filter(PriceTier.training_id == training_id)
        .order_by(asc(PriceTier.min_level_id), asc(PriceTier.max_level_id), asc(PriceTier.id))
        .all()
    )


def serialize_price_tiers(db: Session, training_id: int) -> list[dict]:
    tiers = list_price_tiers(db, training_id)
    out: list[dict] = []
    for t in tiers:
        out.append(
            {
                "id": t.id,
                "label": t.label,
                "min_level_id": t.min_level_id,
                "max_level_id": t.max_level_id,
                "min_level_name": t.min_level.name if getattr(t, "min_level", None) else None,
                "max_level_name": t.max_level.name if getattr(t, "max_level", None) else None,
                "price": float(t.price),
            }
        )
    return out


def get_price_range_for_training(db: Session, training: Training) -> Tuple[Decimal, Decimal]:
    tiers = list_price_tiers(db, training.id)
    prices = [Decimal(str(training.price))]
    prices.extend([Decimal(str(t.price)) for t in tiers])
    return min(prices), max(prices)


def _tier_matches_user_level(t: PriceTier, level_id: int) -> bool:
    if t.min_level_id is not None and level_id < t.min_level_id:
        return False
    if t.max_level_id is not None and level_id > t.max_level_id:
        return False
    return True


def get_effective_training_price(db: Session, training: Training, user: Optional[User]) -> Decimal:
    """
    Final price for a given user.
    Falls back to training.price if no tiers or no user's level.
    """
    base_price = Decimal(str(training.price))

    if user is None or user.level_id is None:
        return base_price

    tiers = list_price_tiers(db, training.id)
    if not tiers:
        return base_price

    matches = [t for t in tiers if _tier_matches_user_level(t, user.level_id)]
    if not matches:
        return base_price

    # Prefer the most specific (narrowest) range. Open-ended bounds are treated as "wide".
    def _width(t: PriceTier) -> int:
        lo = t.min_level_id or 0
        hi = t.max_level_id or 10**9
        return hi - lo

    matches.sort(key=lambda t: (_width(t), t.id))
    return Decimal(str(matches[0].price))


def validate_price_tiers_input(db: Session, tiers: list[dict]) -> None:
    """
    Optional but recommended: validates level IDs and ranges.
    Also prevents obviously invalid ranges (min > max).
    """
    for t in tiers:
        min_id = t.get("min_level_id")
        max_id = t.get("max_level_id")
        if min_id is not None and max_id is not None and min_id > max_id:
            raise ValueError(f"Invalid tier range: min_level_id({min_id}) > max_level_id({max_id})")

    # Check selected levels exist (only if level_id provided)
    level_ids = {x for t in tiers for x in (t.get("min_level_id"), t.get("max_level_id")) if x is not None}
    if level_ids:
        existing = set(
            r[0]
            for r in db.query(Level.id).filter(Level.id.in_(list(level_ids))).all()
        )
        missing = level_ids - existing
        if missing:
            raise ValueError(f"Unknown level_id(s) in price tiers: {sorted(missing)}")


def replace_price_tiers(db: Session, training_id: int, tiers: list[dict]) -> list[PriceTier]:
    """
    Admin helper: replace tiers for a training in one go.
    """
    validate_price_tiers_input(db, tiers)

    db.query(PriceTier).filter(PriceTier.training_id == training_id).delete(synchronize_session=False)

    objs: list[PriceTier] = []
    for t in tiers:
        objs.append(
            PriceTier(
                training_id=training_id,
                label=t.get("label"),
                min_level_id=t.get("min_level_id"),
                max_level_id=t.get("max_level_id"),
                price=Decimal(str(t["price"])),
            )
        )
    db.add_all(objs)
    db.commit()
    return objs
