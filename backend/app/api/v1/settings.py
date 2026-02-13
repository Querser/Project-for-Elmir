from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.db.session import get_db
from app.services.settings_service import (
    DEFAULT_CONTACTS_TEXT,
    DEFAULT_PROMOTIONS_TEXT,
    DEFAULT_RULES_TEXT,
    SettingsService,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/public", response_model=dict)
def get_public_content_settings(
    db: Session = Depends(get_db),
) -> dict:
    """
    Единые тексты разделов для miniapp и Telegram-бота.
    """
    return success_response(
        {
            "contacts_text": SettingsService.get_str(db, "contacts_text", DEFAULT_CONTACTS_TEXT),
            "rules_text": SettingsService.get_str(db, "rules_text", DEFAULT_RULES_TEXT),
            "promotions_text": SettingsService.get_str(db, "promotions_text", DEFAULT_PROMOTIONS_TEXT),
        }
    )
