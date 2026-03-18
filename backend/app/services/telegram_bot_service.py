from __future__ import annotations

import html
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.notification import Notification
from app.models.setting import Setting
from app.models.user import User
from app.services.ban_service import get_active_ban
from app.services.settings_service import (
    DEFAULT_BAN_TEXT,
    DEFAULT_CONTACTS_TEXT,
    DEFAULT_PROMOTIONS_TEXT,
    DEFAULT_RULES_TEXT,
)
from app.services.user_service import get_or_create_user_from_telegram

log = logging.getLogger("app.telegram.bot")


BOT_BTN_OPEN_APP = "MosVolley"
BOT_BTN_OPEN_ADMIN = "Открыть Админ-панель"
BOT_BTN_NOTIFICATIONS = "Уведомления"
BOT_BTN_CONTACTS = "Контакты"
BOT_BTN_RULES = "Правила"
BOT_BTN_PROMOTIONS = "Акции"
BOT_BTN_SHARE_PHONE = "Поделиться номером телефона"




class TelegramBotAPI:
    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def token(self) -> str:
        return (self._settings.telegram_bot_token or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "description": "TELEGRAM_BOT_TOKEN is not configured"}

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = Request(
            url=f"https://api.telegram.org/bot{self.token}/{method}",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if not data.get("ok"):
                log.warning("Telegram API error method=%s payload=%s resp=%s", method, payload, data)
            return data
        except HTTPError as exc:
            raw = ""
            try:
                raw = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            log.warning("Telegram HTTP error method=%s code=%s body=%s", method, exc.code, raw)
            return {"ok": False, "description": f"HTTP {exc.code}", "raw": raw}
        except URLError as exc:
            log.warning("Telegram network error method=%s err=%s", method, exc)
            return {"ok": False, "description": str(exc)}
        except Exception as exc:
            log.exception("Telegram unexpected error method=%s err=%s", method, exc)
            return {"ok": False, "description": str(exc)}

    def send_message(
        self,
        *,
        chat_id: int | str,
        text: str,
        reply_markup: Optional[dict[str, Any]] = None,
        disable_web_page_preview: bool = True,
    ) -> bool:
        payload: dict[str, Any] = {
            "chat_id": int(chat_id),
            "text": text,
            "disable_web_page_preview": bool(disable_web_page_preview),
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        result = self._call("sendMessage", payload)
        return bool(result.get("ok"))

    def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> bool:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        result = self._call("answerCallbackQuery", payload)
        return bool(result.get("ok"))

    def get_user_avatar_url(self, telegram_user_id: int) -> str | None:
        photos_resp = self._call(
            "getUserProfilePhotos",
            {"user_id": int(telegram_user_id), "limit": 1},
        )
        if not photos_resp.get("ok"):
            return None
        photos = (((photos_resp.get("result") or {}).get("photos")) or [])
        if not photos:
            return None
        first_set = photos[0] if isinstance(photos[0], list) and photos[0] else None
        if not first_set:
            return None
        largest = first_set[-1]
        file_id = largest.get("file_id")
        if not file_id:
            return None

        file_resp = self._call("getFile", {"file_id": file_id})
        if not file_resp.get("ok"):
            return None
        file_path = ((file_resp.get("result") or {}).get("file_path") or "").strip()
        if not file_path:
            return None
        return f"https://api.telegram.org/file/bot{self.token}/{file_path}"

    def get_me(self) -> dict[str, Any]:
        return self._call("getMe", {})

    def set_my_name(self, *, name: str, language_code: str = "") -> bool:
        payload: dict[str, Any] = {"name": str(name)}
        if language_code:
            payload["language_code"] = str(language_code)
        result = self._call("setMyName", payload)
        return bool(result.get("ok"))

    def set_chat_menu_button(self, *, chat_id: int | None = None, text: str, url: str) -> bool:
        payload: dict[str, Any] = {
            "menu_button": {
                "type": "web_app",
                "text": str(text),
                "web_app": {"url": str(url)},
            }
        }
        if chat_id is not None:
            payload["chat_id"] = int(chat_id)
        result = self._call("setChatMenuButton", payload)
        return bool(result.get("ok"))

    def set_webhook(self, *, url: str, secret_token: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {"url": url}
        if secret_token:
            payload["secret_token"] = secret_token
        return self._call("setWebhook", payload)

    def delete_webhook(self) -> dict[str, Any]:
        return self._call("deleteWebhook", {"drop_pending_updates": False})


_bot_api = TelegramBotAPI()
_branding_applied = False
_BOOT_WEBAPP_VERSION = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def ensure_telegram_branding() -> None:
    """
    Telegram UI "header" in Mini App shows the bot's display name.
    We also set bot's persistent menu button to open the miniapp with correct label.

    This is best-effort and safe to call multiple times.
    """
    global _branding_applied
    if _branding_applied:
        return
    if not _bot_api.enabled:
        return

    settings = get_settings()

    desired_name = (getattr(settings, "telegram_bot_name", "") or "").strip()
    if desired_name:
        try:
            me = _bot_api.get_me()
            current = ((me.get("result") or {}).get("first_name") or "").strip()
            if current and current != desired_name:
                ok = _bot_api.set_my_name(name=desired_name)
                if ok:
                    log.info("Telegram branding: bot name updated to %r", desired_name)
                else:
                    log.warning("Telegram branding: failed to update bot name to %r", desired_name)
            elif not current:
                # If we can't read current name, still try to set.
                ok = _bot_api.set_my_name(name=desired_name)
                if ok:
                    log.info("Telegram branding: bot name ensured to %r", desired_name)
                else:
                    log.warning("Telegram branding: failed to ensure bot name to %r", desired_name)
        except Exception:
            log.exception("Telegram branding: failed to ensure bot name")

    miniapp_url = _with_webapp_version((settings.telegram_webapp_url or "").strip())
    if miniapp_url:
        try:
            ok = _bot_api.set_chat_menu_button(text=BOT_BTN_OPEN_APP, url=miniapp_url)
            if ok:
                log.info("Telegram branding: chat menu button ensured")
            else:
                log.warning("Telegram branding: failed to ensure chat menu button")
        except Exception:
            log.exception("Telegram branding: failed to ensure chat menu button")

    _branding_applied = True


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _safe_username(username: str | None) -> str | None:
    v = (username or "").strip()
    if not v:
        return None
    return v.lstrip("@")


def _append_url_query_param(url: str, key: str, value: str | int | None) -> str:
    base = (url or "").strip()
    if not base:
        return base
    v = str(value).strip() if value is not None else ""
    if not v:
        return base
    try:
        parts = urlsplit(base)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query[str(key)] = v
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    except Exception:
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}{key}={v}"


def _webapp_version_token() -> str:
    # Optional manual override for emergency cache-busting.
    override = (os.getenv("TELEGRAM_WEBAPP_VERSION") or "").strip()
    if override:
        return override
    return _BOOT_WEBAPP_VERSION


def _with_webapp_version(url: str) -> str:
    return _append_url_query_param(url, "v", _webapp_version_token())


def _extract_bot_command(normalized_text: str) -> str:
    text = (normalized_text or "").strip()
    if not text:
        return ""
    head = text.split(maxsplit=1)[0]
    if not head.startswith("/"):
        return head
    return head.split("@", 1)[0]


def _is_admin_user(user: User) -> bool:
    if bool(getattr(user, "is_admin", False)):
        return True

    raw = (get_settings().telegram_admin_user_id or 0)
    if raw and int(getattr(user, "telegram_id", 0) or 0) == int(raw):
        return True

    dev_admin_ids = (os.getenv("DEV_ADMIN_TELEGRAM_IDS") or "").strip()
    if dev_admin_ids:
        try:
            allowed = {int(x.strip()) for x in dev_admin_ids.split(",") if x.strip()}
            if int(getattr(user, "telegram_id", 0) or 0) in allowed:
                return True
        except Exception:
            pass

    return False


def _main_menu_keyboard(
    *,
    include_admin: bool,
    miniapp_url: str,
    admin_url: str,
    telegram_id: int | None = None,
) -> dict[str, Any]:
    keyboard: list[list[dict[str, Any]]] = []

    miniapp_url = _with_webapp_version(miniapp_url)
    miniapp_url = _append_url_query_param(miniapp_url, "tg_id", telegram_id)
    admin_url = _append_url_query_param(admin_url, "tg_id", telegram_id)

    if miniapp_url:
        keyboard.append(
            [
                {
                    "text": BOT_BTN_OPEN_APP,
                    "web_app": {"url": miniapp_url},
                }
            ]
        )

    if include_admin and admin_url:
        keyboard.append(
            [
                {
                    "text": BOT_BTN_OPEN_ADMIN,
                    "web_app": {"url": admin_url},
                }
            ]
        )

    keyboard.append(
        [
            {"text": BOT_BTN_NOTIFICATIONS},
            {"text": BOT_BTN_CONTACTS},
        ]
    )
    keyboard.append(
        [
            {"text": BOT_BTN_RULES},
            {"text": BOT_BTN_PROMOTIONS},
        ]
    )

    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "is_persistent": True,
    }


def _contact_request_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [[{"text": BOT_BTN_SHARE_PHONE, "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def _get_setting_value(db: Session, key: str, default: str) -> str:
    row = db.query(Setting).filter(Setting.key == key).one_or_none()
    if row is None:
        return default
    value = (row.value or "").strip()
    return value or default


def _html_to_plain_text(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    text = raw
    text = re.sub(r"(?is)<\s*br\s*/?\s*>", "\n", text)
    text = re.sub(r"(?is)</\s*(p|div|h[1-6]|blockquote|pre)\s*>", "\n", text)
    text = re.sub(r"(?is)<\s*(ul|ol)\b[^>]*>", "\n", text)
    text = re.sub(r"(?is)</\s*(ul|ol)\s*>", "\n", text)
    text = re.sub(r"(?is)<\s*li\b[^>]*>", "• ", text)
    text = re.sub(r"(?is)</\s*li\s*>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _format_notification_message(title: str, text: str, url: str | None = None) -> str:
    safe_title = _html_to_plain_text(title) or "Уведомление"
    safe_text = _html_to_plain_text(text)
    chunks = [f"🔔 {safe_title}"]
    if safe_text:
        chunks.append(safe_text)
    if url:
        chunks.append(url)
    msg = "\n\n".join(chunks)
    if len(msg) > 3900:
        msg = msg[:3897] + "..."
    return msg


def send_bot_message_to_user(*, telegram_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> bool:
    return _bot_api.send_message(
        chat_id=telegram_id,
        text=text,
        reply_markup=reply_markup,
    )


def send_bot_notification_to_users(
    db: Session,
    *,
    user_ids: Iterable[int],
    title: str,
    text: str,
    url: str | None = None,
) -> int:
    if not _bot_api.enabled:
        return 0

    normalized_ids = sorted({int(x) for x in user_ids if x is not None})
    if not normalized_ids:
        return 0

    users = db.query(User).filter(User.id.in_(normalized_ids)).all()
    sent = 0
    message = _format_notification_message(title, text, url)
    for user in users:
        tg_id = int(getattr(user, "telegram_id", 0) or 0)
        if not tg_id:
            continue
        if send_bot_message_to_user(telegram_id=tg_id, text=message):
            sent += 1
    return sent


def send_ban_notice_to_user(db: Session, *, user_id: int) -> bool:
    user = db.query(User).filter(User.id == int(user_id)).one_or_none()
    if user is None:
        return False

    tg_id = int(getattr(user, "telegram_id", 0) or 0)
    if not tg_id:
        return False

    text = _format_ban_notice(db, user_id=int(user_id))
    if not text:
        return False

    return send_bot_message_to_user(telegram_id=tg_id, text=text)


def _save_avatar_if_possible(db: Session, user: User) -> None:
    if not hasattr(user, "avatar_url"):
        return
    tg_id = int(getattr(user, "telegram_id", 0) or 0)
    if not tg_id:
        return

    avatar_url = _bot_api.get_user_avatar_url(tg_id)
    if not avatar_url:
        return

    current = (getattr(user, "avatar_url", None) or "").strip()
    if current.startswith("/media/avatars/"):
        # Пользователь установил кастомный аватар в miniapp — не перезаписываем его Telegram-фото.
        return
    if current == avatar_url:
        return

    user.avatar_url = avatar_url
    db.add(user)
    db.commit()
    db.refresh(user)


def _is_profile_complete(user: User) -> bool:
    first_name = (getattr(user, "first_name", None) or "").strip()
    last_name = (getattr(user, "last_name", None) or "").strip()
    phone = (getattr(user, "phone", None) or "").strip()
    return bool(first_name and last_name and phone)


def _try_fill_missing_name_from_text(db: Session, user: User, text: str) -> bool:
    clean = (text or "").strip()
    if not clean:
        return False
    if clean.startswith("/"):
        return False

    lower = _normalize_text(clean)
    if lower in {
        _normalize_text(BOT_BTN_NOTIFICATIONS),
        _normalize_text(BOT_BTN_CONTACTS),
        _normalize_text(BOT_BTN_RULES),
        _normalize_text(BOT_BTN_PROMOTIONS),
        _normalize_text(BOT_BTN_OPEN_APP),
        _normalize_text(BOT_BTN_OPEN_ADMIN),
        _normalize_text(BOT_BTN_SHARE_PHONE),
    }:
        return False

    first_name = (getattr(user, "first_name", None) or "").strip()
    last_name = (getattr(user, "last_name", None) or "").strip()

    if first_name and last_name:
        return False

    parts = [p.strip() for p in clean.split() if p.strip()]
    if not parts:
        return False

    changed = False
    if not first_name:
        user.first_name = parts[0]
        changed = True
        if len(parts) > 1 and not last_name:
            user.last_name = " ".join(parts[1:])
            changed = True
    elif not last_name:
        user.last_name = " ".join(parts)
        changed = True

    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)
    return changed


def _send_profile_prompt(db: Session, user: User) -> None:
    tg_id = int(getattr(user, "telegram_id", 0))
    first_name = (getattr(user, "first_name", None) or "").strip()
    last_name = (getattr(user, "last_name", None) or "").strip()
    phone = (getattr(user, "phone", None) or "").strip()

    if not phone:
        send_bot_message_to_user(
            telegram_id=tg_id,
            text=(
                "Для входа в MosVolley нужен ваш телефон.\n"
                "Нажмите кнопку ниже «Поделиться номером телефона»."
            ),
            reply_markup=_contact_request_keyboard(),
        )
        return

    if not first_name or not last_name:
        send_bot_message_to_user(
            telegram_id=tg_id,
            text="Укажите имя и фамилию одним сообщением (например: Иван Иванов).",
        )
        return


def _format_ban_notice(db: Session, user_id: int) -> str | None:
    active_ban = get_active_ban(db, user_id=user_id)
    if active_ban is None:
        return None

    reason = (getattr(active_ban, "reason", None) or "").strip() or _get_setting_value(
        db,
        "ban_text_default",
        DEFAULT_BAN_TEXT,
    )

    until = getattr(active_ban, "until", None)
    if isinstance(until, datetime):
        until_text = until.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
        until_line = f"До: {until_text}"
    else:
        until_line = "Срок: бессрочно"

    return f"⛔ У вас активный бан.\nПричина: {reason}\n{until_line}"


def _send_ban_notice_if_needed(db: Session, user: User) -> None:
    user_id = int(getattr(user, "id", 0) or 0)
    tg_id = int(getattr(user, "telegram_id", 0) or 0)
    if not user_id or not tg_id:
        return

    text = _format_ban_notice(db, user_id=user_id)
    if not text:
        return
    send_bot_message_to_user(telegram_id=tg_id, text=text)


def _send_main_menu(db: Session, user: User) -> None:
    settings = get_settings()
    tg_id = int(getattr(user, "telegram_id", 0))

    keyboard = _main_menu_keyboard(
        include_admin=_is_admin_user(user),
        miniapp_url=(settings.telegram_webapp_url or "").strip(),
        admin_url=(settings.telegram_admin_webapp_url or "").strip(),
        telegram_id=tg_id,
    )

    send_bot_message_to_user(
        telegram_id=tg_id,
        text=(
            "Профиль готов. Вы можете открыть MosVolley, смотреть уведомления,"
            " контакты, правила и акции."
        ),
        reply_markup=keyboard,
    )


def _send_start_flow(db: Session, user: User, *, is_new_user: bool) -> None:
    _send_ban_notice_if_needed(db, user)
    if _is_profile_complete(user):
        _send_main_menu(db, user)
        return

    tg_id = int(getattr(user, "telegram_id", 0) or 0)
    if tg_id:
        intro_text = (
            "Добро пожаловать в MosVolley.\n"
            "Чтобы открыть мини-приложение, нужно завершить регистрацию."
            if is_new_user
            else "Ваш профиль заполнен не полностью. Давайте завершим регистрацию."
        )
        send_bot_message_to_user(
            telegram_id=tg_id,
            text=intro_text,
        )
    _send_profile_prompt(db, user)


def _send_notifications_list(db: Session, user: User) -> None:
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )
    tg_id = int(getattr(user, "telegram_id", 0))

    if not rows:
        send_bot_message_to_user(telegram_id=tg_id, text="У вас пока нет уведомлений.")
        return

    lines = ["Последние уведомления:"]
    for item in rows:
        dt = getattr(item, "created_at", None)
        dt_text = ""
        if isinstance(dt, datetime):
            dt_local = dt.astimezone(timezone.utc)
            dt_text = dt_local.strftime("%d.%m %H:%M")
        title = _html_to_plain_text(getattr(item, "title", "")) or "Уведомление"
        body = _html_to_plain_text(getattr(item, "text", ""))
        if len(body) > 120:
            body = body[:117] + "..."
        if dt_text:
            lines.append(f"• [{dt_text}] {title}: {body}")
        else:
            lines.append(f"• {title}: {body}")

    msg = "\n".join(lines)
    if len(msg) > 3900:
        msg = msg[:3897] + "..."
    send_bot_message_to_user(telegram_id=tg_id, text=msg)


def _process_contact(db: Session, message: dict[str, Any], user: User) -> None:
    contact = message.get("contact") or {}
    sender = message.get("from") or {}
    from_user_id = int(sender.get("id") or 0)
    contact_user_id = int(contact.get("user_id") or 0)
    phone_raw = (contact.get("phone_number") or "").strip()
    tg_id = int(getattr(user, "telegram_id", 0))

    if not phone_raw:
        send_bot_message_to_user(telegram_id=tg_id, text="Не удалось прочитать номер телефона. Попробуйте еще раз.")
        _send_profile_prompt(db, user)
        return

    if from_user_id and contact_user_id and from_user_id != contact_user_id:
        send_bot_message_to_user(
            telegram_id=tg_id,
            text="Нужно отправить именно ваш номер телефона.",
        )
        _send_profile_prompt(db, user)
        return

    try:
        refreshed = get_or_create_user_from_telegram(
            db,
            telegram_id=tg_id,
            username=getattr(user, "username", None),
            first_name=getattr(user, "first_name", None),
            last_name=getattr(user, "last_name", None),
            phone=phone_raw,
        )
    except Exception:
        log.exception("Failed to save contact phone for tg_id=%s", tg_id)
        send_bot_message_to_user(
            telegram_id=tg_id,
            text="Не удалось сохранить номер. Проверьте формат и попробуйте еще раз.",
        )
        _send_profile_prompt(db, user)
        return

    if _is_profile_complete(refreshed):
        _send_main_menu(db, refreshed)
        return

    _send_profile_prompt(db, refreshed)


def _handle_text_command(db: Session, user: User, text: str, *, is_new_user: bool = False) -> None:
    normalized = _normalize_text(text)
    tg_id = int(getattr(user, "telegram_id", 0))
    command = _extract_bot_command(normalized)

    if command in {"/start", "/menu"} or normalized in {"start", "menu"}:
        _send_start_flow(db, user, is_new_user=is_new_user)
        return

    if normalized == _normalize_text(BOT_BTN_NOTIFICATIONS):
        _send_notifications_list(db, user)
        return

    if normalized == _normalize_text(BOT_BTN_CONTACTS):
        contacts = _get_setting_value(db, "contacts_text", DEFAULT_CONTACTS_TEXT)
        send_bot_message_to_user(telegram_id=tg_id, text=contacts)
        return

    if normalized == _normalize_text(BOT_BTN_RULES):
        rules = _get_setting_value(db, "rules_text", DEFAULT_RULES_TEXT)
        send_bot_message_to_user(telegram_id=tg_id, text=rules)
        return

    if normalized == _normalize_text(BOT_BTN_PROMOTIONS):
        promotions = _get_setting_value(db, "promotions_text", DEFAULT_PROMOTIONS_TEXT)
        send_bot_message_to_user(telegram_id=tg_id, text=promotions)
        return

    if not _is_profile_complete(user) and _try_fill_missing_name_from_text(db, user, text):
        updated = db.query(User).filter(User.id == user.id).one()
        if _is_profile_complete(updated):
            _send_main_menu(db, updated)
        else:
            _send_profile_prompt(db, updated)
        return

    send_bot_message_to_user(
        telegram_id=tg_id,
        text=(
            "Команда не распознана.\n"
            "Используйте кнопки меню или команду /start."
        ),
    )


def handle_telegram_update(db: Session, update: dict[str, Any]) -> dict[str, Any]:
    message = update.get("message")
    if message:
        user_obj = message.get("from") or {}
        tg_id = int(user_obj.get("id") or 0)
        if not tg_id:
            return {"handled": False, "reason": "no_user_id"}

        existing_user = db.query(User).filter(User.telegram_id == tg_id).one_or_none()
        is_new_user = existing_user is None
        user = get_or_create_user_from_telegram(
            db,
            telegram_id=tg_id,
            username=_safe_username(user_obj.get("username")),
            first_name=(user_obj.get("first_name") or "").strip() or None,
            last_name=(user_obj.get("last_name") or "").strip() or None,
        )
        _save_avatar_if_possible(db, user)

        if message.get("contact"):
            _process_contact(db, message, user)
            return {"handled": True, "kind": "contact"}

        text = (message.get("text") or "").strip()
        if text:
            _handle_text_command(db, user, text, is_new_user=is_new_user)
            return {"handled": True, "kind": "text"}

        send_bot_message_to_user(
            telegram_id=tg_id,
            text="Поддерживаются текстовые команды и отправка контакта.",
        )
        return {"handled": True, "kind": "unsupported_message"}

    callback = update.get("callback_query")
    if callback:
        callback_id = str(callback.get("id") or "")
        if callback_id:
            _bot_api.answer_callback_query(callback_id, "Откройте меню через /start")
        return {"handled": True, "kind": "callback_query"}

    return {"handled": False, "reason": "unsupported_update"}


def webhook_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "bot_enabled": _bot_api.enabled,
        "webhook_url": (settings.telegram_webhook_url or "").strip(),
        "webhook_secret_configured": bool((settings.telegram_bot_webhook_secret or "").strip()),
    }


def set_bot_webhook(*, webhook_url: str, secret_token: str = "") -> dict[str, Any]:
    return _bot_api.set_webhook(url=webhook_url, secret_token=secret_token)


def delete_bot_webhook() -> dict[str, Any]:
    return _bot_api.delete_webhook()
