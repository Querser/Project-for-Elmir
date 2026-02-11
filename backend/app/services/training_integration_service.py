from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote_plus

from app.core.config import get_settings


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        val = float(value)
    except Exception:
        return None
    if val != val:  # NaN guard
        return None
    return val


def _get_location_label(training: Any) -> str:
    location = getattr(training, "location", None)
    candidates = [
        getattr(location, "address", None) if location is not None else None,
        getattr(location, "name", None) if location is not None else None,
        getattr(training, "location_name", None),
        getattr(training, "address", None),
        getattr(training, "location", None) if isinstance(getattr(training, "location", None), str) else None,
    ]
    for item in candidates:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            return text
    return ""


def _get_lat_lon(training: Any) -> tuple[float | None, float | None]:
    location = getattr(training, "location", None)
    lat = _to_float(getattr(training, "latitude", None))
    lon = _to_float(getattr(training, "longitude", None))

    if lat is None and location is not None:
        lat = _to_float(getattr(location, "latitude", None))
    if lon is None and location is not None:
        lon = _to_float(getattr(location, "longitude", None))
    return lat, lon


def build_yandex_map_payload(training: Any) -> dict[str, Any]:
    label = _get_location_label(training)
    lat, lon = _get_lat_lon(training)

    payload: dict[str, Any] = {
        "provider": "yandex",
        "label": label or None,
        "latitude": lat,
        "longitude": lon,
        "open_url": None,
        "route_url": None,
        "widget_url": None,
    }

    if lat is not None and lon is not None:
        ll = f"{lon},{lat}"
        payload["open_url"] = f"https://yandex.ru/maps/?ll={quote_plus(ll)}&z=15&pt={quote_plus(ll)},pm2rdm"
        payload["route_url"] = f"https://yandex.ru/maps/?mode=routes&rtext=~{lat},{lon}&rtt=auto"
        payload["widget_url"] = f"https://yandex.ru/map-widget/v1/?ll={quote_plus(ll)}&z=15&pt={quote_plus(ll)},pm2rdm&lang=ru_RU"
        return payload

    if label:
        encoded = quote_plus(label)
        payload["open_url"] = f"https://yandex.ru/maps/?text={encoded}"
        payload["route_url"] = f"https://yandex.ru/maps/?mode=routes&rtext=~{encoded}&rtt=auto"
        payload["widget_url"] = f"https://yandex.ru/map-widget/v1/?text={encoded}&z=15&lang=ru_RU"

    return payload


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_google_dt(dt: datetime) -> str:
    return _to_utc(dt).strftime("%Y%m%dT%H%M%SZ")


def _format_ics_dt(dt: datetime) -> str:
    return _to_utc(dt).strftime("%Y%m%dT%H%M%SZ")


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def build_training_calendar_payload(training: Any, *, base_api_url: str = "") -> dict[str, Any]:
    start_at = getattr(training, "start_at", None)
    if not isinstance(start_at, datetime):
        return {"google_url": None, "ics_url": None, "apple_ics_url": None}

    duration = int(getattr(training, "duration_minutes", 0) or 0)
    if duration <= 0:
        duration = 90
    end_at = start_at + timedelta(minutes=duration)

    title = (getattr(training, "title", None) or "Тренировка").strip()
    description = (getattr(training, "description", None) or "").strip()
    location_text = _get_location_label(training)

    settings = get_settings()
    webapp_url = (settings.telegram_webapp_url or "").strip()
    if webapp_url and getattr(training, "id", None):
        separator = "\n\n" if description else ""
        description = f"{description}{separator}Mini App: {webapp_url}"

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{_format_google_dt(start_at)}/{_format_google_dt(end_at)}",
        "details": description,
        "location": location_text,
    }
    query = "&".join(f"{k}={quote_plus(v)}" for k, v in params.items() if v)
    google_url = f"https://calendar.google.com/calendar/render?{query}"

    base = (base_api_url or "").rstrip("/")
    training_id = getattr(training, "id", None)
    ics_url = f"{base}/api/v1/trainings/{training_id}/calendar.ics" if base and training_id else None

    return {
        "google_url": google_url,
        "ics_url": ics_url,
        "apple_ics_url": ics_url,
        "start_at": _to_utc(start_at).isoformat(),
        "end_at": _to_utc(end_at).isoformat(),
    }


def build_training_ics_content(training: Any) -> str:
    start_at = getattr(training, "start_at", None)
    if not isinstance(start_at, datetime):
        raise ValueError("Training has no valid start_at")

    duration = int(getattr(training, "duration_minutes", 0) or 0)
    if duration <= 0:
        duration = 90
    end_at = start_at + timedelta(minutes=duration)

    title = _ics_escape((getattr(training, "title", None) or "Тренировка").strip())
    description = _ics_escape((getattr(training, "description", None) or "").strip())
    location_text = _ics_escape(_get_location_label(training))
    uid = f"training-{getattr(training, 'id', 'unknown')}@volleyball-miniapp"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Elmir Volleyball//MiniApp//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_format_ics_dt(datetime.now(timezone.utc))}",
        f"DTSTART:{_format_ics_dt(start_at)}",
        f"DTEND:{_format_ics_dt(end_at)}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{description}",
        f"LOCATION:{location_text}",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    return "\r\n".join(lines)

