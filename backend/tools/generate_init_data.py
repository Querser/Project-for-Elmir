from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote

from app.core.config import settings
from app.core.telegram_auth import _compute_hash


def main() -> None:
    bot_token = settings.telegram_bot_token
    if not bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN не задан. "
            "Добавь его в .env.dev или переменные окружения."
        )

    # Тестовый пользователь
    user = {
        "id": 123456789,
        "first_name": "Test",
        "last_name": "User",
        "username": "test_user",
        "language_code": "ru",
    }

    auth_date = int(datetime.now(tz=timezone.utc).timestamp())

    data = {
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
        "auth_date": str(auth_date),
        "query_id": "TEST_QUERY_ID",
    }

    hash_value = _compute_hash(data, bot_token)

    parts = [
        f"user={quote(data['user'], safe='')}",
        f"auth_date={quote(data['auth_date'], safe='')}",
        f"query_id={quote(data['query_id'], safe='')}",
        f"hash={hash_value}",
    ]
    init_data = "&".join(parts)

    print("Сгенерирован X-Telegram-Init-Data.\n")
    print(f"telegram_id пользователя: {user['id']}\n")
    print("Скопируй ЭТУ строку целиком в заголовок X-Telegram-Init-Data:\n")
    print(init_data)
    print("\nПример команды в PowerShell:")
    print(f'  $init = "{init_data}"')
    print('  curl.exe -H "X-Telegram-Init-Data: $init" http://localhost:8001/api/v1/profile/me')


if __name__ == "__main__":
    main()
