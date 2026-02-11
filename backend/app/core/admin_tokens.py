from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict


class AdminTokenError(Exception):
    pass


def _strip_wrapping_quotes(value: str) -> str:
    v = (value or "").strip()
    while len(v) >= 2 and v[0] == v[-1] and v[0] in {"'", '"'}:
        v = v[1:-1].strip()
    return v


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    s = data.strip()
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _get_secret() -> str:
    secret = _strip_wrapping_quotes(os.getenv("ADMIN_TOKEN_SECRET") or "")
    if not secret or secret.startswith("CHANGE_ME"):
        raise AdminTokenError("ADMIN_TOKEN_SECRET is not configured")
    return secret


def _get_version() -> str:
    return _strip_wrapping_quotes(os.getenv("ADMIN_TOKEN_VERSION") or "1") or "1"


def _now() -> int:
    return int(time.time())


def _ttl_access_seconds() -> int:
    raw = _strip_wrapping_quotes(os.getenv("ADMIN_ACCESS_TOKEN_TTL_MINUTES") or "30")
    try:
        m = int(raw)
    except Exception:
        m = 30
    return max(60, m * 60)


def _ttl_refresh_seconds() -> int:
    raw = _strip_wrapping_quotes(os.getenv("ADMIN_REFRESH_TOKEN_TTL_DAYS") or "14")
    try:
        d = int(raw)
    except Exception:
        d = 14
    return max(3600, d * 24 * 3600)


def _sign(msg: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
    return _b64url_encode(sig)


def _encode(payload: Dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    p = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    msg = f"{h}.{p}".encode("utf-8")
    s = _sign(msg, secret)
    return f"{h}.{p}.{s}"


def _decode(token: str, secret: str) -> Dict[str, Any]:
    parts = (token or "").split(".")
    if len(parts) != 3:
        raise AdminTokenError("Invalid token format")

    h, p, s = parts
    msg = f"{h}.{p}".encode("utf-8")
    expected = _sign(msg, secret)
    if not hmac.compare_digest(expected, s):
        raise AdminTokenError("Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(p).decode("utf-8"))
    except Exception:
        raise AdminTokenError("Invalid token payload")

    if not isinstance(payload, dict):
        raise AdminTokenError("Invalid token payload")

    return payload


def issue_admin_tokens(username: str) -> Dict[str, Any]:
    secret = _get_secret()
    ver = _get_version()
    now = _now()

    access_payload = {
        "typ": "access",
        "username": username,
        "sub": "admin",
        "ver": ver,
        "iat": now,
        "exp": now + _ttl_access_seconds(),
        "jti": secrets.token_urlsafe(16),
    }
    refresh_payload = {
        "typ": "refresh",
        "username": username,
        "sub": "admin",
        "ver": ver,
        "iat": now,
        "exp": now + _ttl_refresh_seconds(),
        "jti": secrets.token_urlsafe(16),
    }

    return {
        "access_token": _encode(access_payload, secret),
        "refresh_token": _encode(refresh_payload, secret),
        "token_type": "bearer",
        "access_expires_in": access_payload["exp"] - now,
    }


def verify_admin_access_token(token: str) -> Dict[str, Any]:
    secret = _get_secret()
    ver = _get_version()

    payload = _decode(token, secret)

    if payload.get("typ") != "access":
        raise AdminTokenError("Not an access token")
    if payload.get("sub") != "admin":
        raise AdminTokenError("Invalid subject")
    if str(payload.get("ver")) != str(ver):
        raise AdminTokenError("Token version mismatch")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise AdminTokenError("Invalid exp")
    if _now() >= exp:
        raise AdminTokenError("Token expired")

    return payload


def verify_admin_refresh_token(token: str) -> Dict[str, Any]:
    secret = _get_secret()
    ver = _get_version()

    payload = _decode(token, secret)

    if payload.get("typ") != "refresh":
        raise AdminTokenError("Not a refresh token")
    if payload.get("sub") != "admin":
        raise AdminTokenError("Invalid subject")
    if str(payload.get("ver")) != str(ver):
        raise AdminTokenError("Token version mismatch")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise AdminTokenError("Invalid exp")
    if _now() >= exp:
        raise AdminTokenError("Token expired")

    return payload
