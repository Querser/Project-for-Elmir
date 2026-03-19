from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_admin_user_any, get_db
from app.core.responses import success_response
from app.services.telegram_bot_service import (
    begin_telegram_webhook_response_mode,
    delete_bot_webhook,
    finish_telegram_webhook_response_mode,
    handle_telegram_update,
    set_bot_webhook,
    webhook_status,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])
log = logging.getLogger("app.telegram.webhook")


def _diag(message: str) -> None:
    print(f"[TELEGRAM_DIAG] {message}", flush=True)


class WebhookConfigIn(BaseModel):
    url: str | None = Field(default=None, max_length=1000)
    secret_token: str | None = Field(default=None, max_length=256)


@router.post("/webhook", response_model=dict)
def telegram_webhook(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    update_id = payload.get("update_id")
    log.info(
        "Telegram webhook request path=%s update_id=%s has_message=%s has_callback=%s",
        request.url.path,
        update_id,
        bool(payload.get("message") or payload.get("edited_message")),
        bool(payload.get("callback_query")),
    )
    _diag(
        f"webhook_request path={request.url.path} update_id={update_id} "
        f"has_message={bool(payload.get('message') or payload.get('edited_message'))} "
        f"has_callback={bool(payload.get('callback_query'))}"
    )
    settings = get_settings()
    expected_secret = (settings.telegram_bot_webhook_secret or "").strip()
    if expected_secret:
        provided = (request.headers.get("X-Telegram-Bot-Api-Secret-Token") or "").strip()
        if provided and provided != expected_secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
        if not provided:
            log.warning("Telegram webhook called without secret header while secret is configured")

    tokens = begin_telegram_webhook_response_mode()
    try:
        result = handle_telegram_update(db, payload)
    finally:
        queued_commands = finish_telegram_webhook_response_mode(tokens)

    if queued_commands:
        command = queued_commands[0]
        if len(queued_commands) > 1:
            log.warning(
                "Telegram webhook queued %s response methods, returning only first method=%s",
                len(queued_commands),
                command.get("method"),
            )
        _diag(
            f"webhook_response_method update_id={update_id} method={command.get('method')} "
            f"chat_id={command.get('chat_id')}"
        )
        return command

    log.info(
        "Telegram webhook handled update_id=%s handled=%s kind=%s reason=%s",
        update_id,
        bool(result.get("handled")),
        result.get("kind"),
        result.get("reason"),
    )
    _diag(
        f"webhook_handled update_id={update_id} handled={bool(result.get('handled'))} "
        f"kind={result.get('kind')} reason={result.get('reason')}"
    )
    return {"ok": True, "result": result}


@router.post("", response_model=dict)
@router.post("/", response_model=dict)
@router.post("/update", response_model=dict)
def telegram_webhook_compat(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return telegram_webhook(payload=payload, request=request, db=db)


@router.get("/webhook/status", response_model=dict)
def telegram_webhook_status(
    _admin: Any = Depends(get_current_admin_user_any),
) -> dict[str, Any]:
    return success_response(webhook_status())


@router.post("/webhook/set", response_model=dict)
def telegram_set_webhook(
    body: WebhookConfigIn,
    _admin: Any = Depends(get_current_admin_user_any),
) -> dict[str, Any]:
    settings = get_settings()
    webhook_url = (body.url or settings.telegram_webhook_url or "").strip()
    if not webhook_url:
        raise HTTPException(status_code=422, detail="Webhook URL is required")

    secret = (body.secret_token or settings.telegram_bot_webhook_secret or "").strip()
    result = set_bot_webhook(webhook_url=webhook_url, secret_token=secret)
    return success_response(result)


@router.post("/webhook/delete", response_model=dict)
def telegram_remove_webhook(
    _admin: Any = Depends(get_current_admin_user_any),
) -> dict[str, Any]:
    result = delete_bot_webhook()
    return success_response(result)
