# backend/tools/generate_init_data.py
import os
import sys
import hmac
import hashlib
import json
import argparse
import urllib.parse
from datetime import datetime, timezone

sys.path.append("/app")

try:
    from app.db.session import SessionLocal
    from app.models.user import User
except Exception:
    SessionLocal = None
    User = None


def generate_init_data(
    secret: str,
    user_json: dict,
    auth_date: int | None = None,
    query_id: str = "AAHqZ_DEMO_QUERY_ID",
) -> str:
    if auth_date is None:
        auth_date = int(datetime.now(timezone.utc).timestamp())

    # Важно: строка для хэша использует значения без URL-энкодинга
    user_str = json.dumps(user_json, separators=(",", ":"), ensure_ascii=False)
    data_check_string = f"auth_date={auth_date}\nquery_id={query_id}\nuser={user_str}"

    secret_key = hmac.new(b"WebAppData", secret.encode("utf-8"), hashlib.sha256).digest()
    hash_value = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    init_data = (
        f"auth_date={auth_date}"
        f"&query_id={query_id}"
        f"&user={urllib.parse.quote(user_str)}"
        f"&hash={hash_value}"
    )
    return init_data


def try_load_user_from_db(telegram_id: int | None, username: str | None) -> dict | None:
    if SessionLocal is None or User is None:
        return None

    try:
        with SessionLocal() as db:
            q = db.query(User)
            if telegram_id is not None:
                q = q.filter(User.telegram_id == telegram_id)
            elif username:
                q = q.filter(User.telegram_username == username.lstrip("@"))
            else:
                return None

            user = q.first()
            if not user:
                return None

            # full_name может быть None
            full_name = getattr(user, "full_name", None) or "Demo User"

            # Telegram user json (минимально необходимый набор полей)
            return {
                "id": int(user.telegram_id),
                "first_name": full_name.split(" ")[0] if full_name else "Demo",
                "last_name": " ".join(full_name.split(" ")[1:]) if len(full_name.split(" ")) > 1 else "",
                "username": (getattr(user, "telegram_username", None) or "").lstrip("@"),
                "language_code": "ru",
                "is_premium": False,
            }
    except Exception:
        # Если БД недоступна — просто вернём None и упадём на фейковые данные ниже
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate Telegram WebApp initData for local/dev testing.")
    parser.add_argument("--telegram-id", type=int, default=123456789, help="Telegram numeric user id")
    parser.add_argument("--username", type=str, default=None, help="Telegram username (optional)")
    parser.add_argument("--secret", type=str, default=os.getenv("INIT_DATA_SECRET"), help="INIT_DATA_SECRET")
    parser.add_argument("--query-id", type=str, default="AAHqZ_DEMO_QUERY_ID", help="query_id")
    args = parser.parse_args()

    if not args.secret:
        raise ValueError("❌ INIT_DATA_SECRET is not set. Provide --secret or set INIT_DATA_SECRET env var.")

    db_user_json = try_load_user_from_db(args.telegram_id, args.username)

    if db_user_json:
        user_json = db_user_json
    else:
        # fallback (если БД недоступна или пользователь не найден)
        username = (args.username or "test_user").lstrip("@")
        user_json = {
            "id": args.telegram_id,
            "first_name": "Test",
            "last_name": "User",
            "username": username,
            "language_code": "ru",
            "is_premium": False,
        }

    init_data = generate_init_data(
        secret=args.secret,
        user_json=user_json,
        query_id=args.query_id,
    )

    print("✅ initData generated:")
    print(init_data)
    print()
    print("PowerShell (пример):")
    print(f'$env:TG_INIT_DATA="{init_data}"')
    print()
    print("User used:")
    print(json.dumps(user_json, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()