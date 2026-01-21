import { API_ENDPOINTS, apiFetch } from "./api";
import { getMonday, toISODate } from "./date";
import type { LocationOption, Training } from "../types";
import { normalizeTrainingFromApi } from "./normalize";

/**
 * Строим query под бэк максимально универсально:
 * - date=YYYY-MM-DD (как у тебя было)
 * - type=...
 * - level=...
 * - location=... (универсально) + address=... (на случай другого имени)
 */
export function buildTrainingsQuery(params: {
  date: Date;
  filters: { type: Set<string>; level: Set<string>; location: Set<string> };
}): string {
  const qs = new URLSearchParams();
  qs.set("date", toISODate(params.date));

  if (params.filters.type.size) qs.set("type", Array.from(params.filters.type).join(","));
  if (params.filters.level.size) qs.set("level", Array.from(params.filters.level).join(","));

  if (params.filters.location.size) {
    const v = Array.from(params.filters.location).join(",");
    qs.set("location", v);
    qs.set("address", v); // fallback, если бэк фильтрует по address
  }

  const s = qs.toString();
  return s ? `?${s}` : "";
}

export async function loadTrainings(opts: {
  token: string;
  date: Date;
  filters: { type: Set<string>; level: Set<string>; location: Set<string> };
}): Promise<Training[]> {
  const q = buildTrainingsQuery({ date: opts.date, filters: opts.filters });
  const data: any = await apiFetch(API_ENDPOINTS.trainings + q, { token: opts.token });

  const items = data?.items || data?.result?.items || data?.data?.items || data || [];
  const arr = Array.isArray(items) ? items : [];
  return arr.map(normalizeTrainingFromApi);
}

/**
 * ВАЖНО по ТЗ пользователя:
 * "локации берутся из БД => если есть тренировка с адресом ..., то адрес показывается в фильтре"
 *
 * Универсально делаем так:
 * 1) Пытаемся спросить /api/v1/locations (если существует)
 * 2) Если нет — собираем уникальные locationDisplay из тренировок за текущую неделю (7 запросов по date).
 */
export async function loadLocationsUniversal(opts: {
  token: string;
  dateInWeek: Date;
}): Promise<LocationOption[]> {
  // 1) пробуем locations endpoint
  try {
    const data: any = await apiFetch(API_ENDPOINTS.locations, { token: opts.token });
    const items = data?.items || data?.result?.items || data?.data?.items || data || [];
    const arr = Array.isArray(items) ? items : [];

    // ждём что бэк может вернуть: {title,address} или просто строку
    const out: LocationOption[] = arr
      .map((x: any) => {
        if (typeof x === "string") {
          const t = x.trim();
          if (!t) return null;
          return { key: t, title: t };
        }
        const title = (x.title || x.name || x.locationTitle || "").toString().trim();
        const address = (x.address || x.locationAddress || "").toString().trim();
        const display = title && address ? `${title} · ${address}` : (address || title || "");
        const v = display.trim();
        if (!v) return null;
        return { key: v, title: v };
      })
      .filter(Boolean) as LocationOption[];

    // уникализация
    return uniqLocations(out);
  } catch {
    // ignore -> fallback to trainings scan
  }

  // 2) fallback: собираем из тренировок за неделю
  const monday = getMonday(opts.dateInWeek);
  const all: string[] = [];

  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);

    try {
      // грузим без фильтров, чтобы собрать все адреса
      const list = await loadTrainings({
        token: opts.token,
        date: d,
        filters: { type: new Set(), level: new Set(), location: new Set() },
      });

      for (const t of list) {
        const v = (t.locationDisplay || "").trim();
        if (v && v !== "Адрес не указан") all.push(v);
      }
    } catch {
      // skip day
    }
  }

  const optsArr: LocationOption[] = Array.from(new Set(all)).map((v) => ({ key: v, title: v }));
  return uniqLocations(optsArr);
}

function uniqLocations(arr: LocationOption[]): LocationOption[] {
  const seen = new Set<string>();
  const out: LocationOption[] = [];
  for (const x of arr) {
    const k = x.key.trim();
    if (!k) continue;
    if (seen.has(k)) continue;
    seen.add(k);
    out.push({ key: k, title: x.title });
  }
  return out;
}
