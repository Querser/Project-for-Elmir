# backend/app/core/security.py
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict
from urllib.parse import parse_qsl


class TelegramInitDataError(ValueError):
    pass


def verify_telegram_init_data(init_data: str, bot_token: str) -> Dict[str, Any]:
    """
    Validates Telegram WebApp initData and returns parsed payload.
    Expects init_data as querystring: "query_id=...&user=...&auth_date=...&hash=..."
    """
    if not init_data:
        raise TelegramInitDataError("Empty init data")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise TelegramInitDataError("Missing hash in init data")

    # data_check_string: key=value sorted by key, joined by \n
    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs.keys()))

    # secret_key = HMAC_SHA256("WebAppData", bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramInitDataError("Invalid init data hash")

    # parse user json if present
    if "user" in pairs:
        try:
            pairs["user"] = json.loads(pairs["user"])
        except Exception as e:
            raise TelegramInitDataError(f"Invalid user json: {e}") from e

    return pairs
