import type { Training } from "../types";
import { addMinutes, formatTimeHHMM, pad2 } from "./date";

/**
 * Делает объект тренировки универсальным под разные ответы бэка.
 * Важное: locationDisplay = "Название · Адрес" или просто адрес (если названия нет)
 */
export function normalizeTrainingFromApi(x: any): Training {
  const start =
    x.start_at || x.starts_at || x.startsAt || x.startsAtUtc || x.startAt || x.start || null;

  const end = x.ends_at || x.endsAt || x.end_at || x.endAt || x.end || null;

  const duration = Number(x.duration_minutes || x.duration || 0) || 0;

  const endDate = end ? new Date(end) : (start && duration ? addMinutes(start, duration) : null);

  const time = start ? formatTimeHHMM(start) : "—";
  const timeRange =
    start && endDate
      ? `${formatTimeHHMM(start)}–${pad2(endDate.getHours())}:${pad2(endDate.getMinutes())}`
      : (start ? `${formatTimeHHMM(start)}–—` : "—");

  // уровни допуска
  let levels: string[] = [];
  if (Array.isArray(x.levels) && x.levels.length) levels = x.levels;
  else if (Array.isArray(x.allowed_levels) && x.allowed_levels.length) levels = x.allowed_levels;
  else if (x.min_level_name || x.max_level_name) {
    const a = x.min_level_name ? [String(x.min_level_name)] : [];
    const b =
      x.max_level_name && x.max_level_name !== x.min_level_name ? [String(x.max_level_name)] : [];
    levels = [...a, ...b];
  } else if (x.level) {
    levels = [String(x.level)];
  }

  const capacity = Number(x.capacity_main ?? x.capacity ?? x.max_participants ?? 0) || 0;
  const freeRaw = Number(x.free_places ?? x.free ?? x.free_slots ?? NaN);
  const occupiedRaw = Number(x.occupied_main ?? x.occupied ?? x.booked ?? 0) || 0;
  const free = Number.isFinite(freeRaw) ? freeRaw : Math.max(0, capacity - occupiedRaw);
  const occupied = Number.isFinite(freeRaw) ? Math.max(0, capacity - freeRaw) : occupiedRaw;

  // location title + address
  const address =
    x.address || x.location_address || x.location?.address || x.location_name || x.location || "";

  const locationTitle =
    x.location_title ||
    x.locationTitle ||
    x.location?.title ||
    x.location?.name ||
    x.place_name ||
    x.place ||
    "";

  const addressText = (address || "").toString().trim();
  const locTitleText = (locationTitle || "").toString().trim();

  const locationDisplay = locTitleText && addressText
    ? `${locTitleText} · ${addressText}`
    : (addressText || locTitleText || "Адрес не указан");

  return {
    id: x.id,
    title: x.title || x.name || "Тренировка",
    titleFull: x.title || x.name || "Тренировка",

    start_at: start,
    time,
    timeRange,

    address: addressText || "Адрес не указан",
    locationTitle: locTitleText || undefined,
    locationDisplay,

    trainer: x.coach_name || x.trainer || x.coach?.name || "—",
    levels,

    capacity,
    free,
    occupied,

    price: Number(x.price_min ?? x.price ?? x.cost ?? 0) || 0,

    can_enroll: typeof x.can_enroll === "boolean" ? x.can_enroll : true,
    user_enrollment_status: x.user_enrollment_status || x.enrollment_status || "none",

    with_coach:
      typeof x.with_coach === "boolean"
        ? x.with_coach
        : Boolean(x.coach_name || x.trainer || x.coach),

    image_url: x.image_url || x.image || null,
  };
}
