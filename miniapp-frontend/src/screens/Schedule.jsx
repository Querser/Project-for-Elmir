// src/screens/Schedule.jsx
import { useMemo, useState } from "react";

const RU_WEEK = ["ВС", "ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ"];

function ymd(d) {
  const dt = new Date(d);
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const day = String(dt.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function sameLocalDay(a, b) {
  const da = new Date(a);
  const db = new Date(b);
  return (
    da.getFullYear() === db.getFullYear() &&
    da.getMonth() === db.getMonth() &&
    da.getDate() === db.getDate()
  );
}

function startOfWeekMonday(date) {
  const d = new Date(date);
  const day = d.getDay(); // 0=Sun..6=Sat
  const diff = (day + 6) % 7; // Monday=0
  d.setDate(d.getDate() - diff);
  d.setHours(12, 0, 0, 0);
  return d;
}

function buildWeek(date) {
  const start = startOfWeekMonday(date);
  const out = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    out.push(d);
  }
  return out;
}

function ruLongDate(d) {
  const s = new Date(d).toLocaleDateString("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function ruTime(dt) {
  if (!dt) return "";
  try {
    return new Date(dt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function getText(t, keys) {
  for (const k of keys) {
    const v = k.split(".").reduce((acc, part) => (acc ? acc[part] : undefined), t);
    if (v != null && String(v).trim() !== "") return String(v);
  }
  return "";
}

function normalize(s) {
  return String(s || "").trim().toLowerCase();
}

function uniq(arr) {
  const seen = new Set();
  const out = [];
  for (const x of arr) {
    const k = normalize(x);
    if (!k) continue;
    if (!seen.has(k)) {
      seen.add(k);
      out.push(x);
    }
  }
  return out;
}

function statusLabel(statusRaw) {
  const s = normalize(statusRaw);
  if (!s || s === "none") return { text: "Не записан", kind: "muted" };
  if (s === "main" || s === "enrolled" || s === "booked") return { text: "Записан", kind: "success" };
  if (s === "reserve" || s === "waitlist") return { text: "Резерв", kind: "warning" };
  if (s === "not_allowed" || s === "forbidden") return { text: "Недоступно", kind: "danger" };
  return { text: statusRaw, kind: "muted" };
}

export default function Schedule({
  trainings,
  loading,
  error,
  onRefresh, // ({ date, types, levels, locations, coaches })
  onOpenTraining,
}) {
  const [selectedDate, setSelectedDate] = useState(() => new Date());
  const [filtersOpen, setFiltersOpen] = useState(false);

  const [filters, setFilters] = useState({
    types: [],
    levels: [],
    locations: [],
    coaches: [],
  });

  const week = useMemo(() => buildWeek(selectedDate), [selectedDate]);

  const options = useMemo(() => {
    const types = [];
    const levels = [];
    const locations = [];
    const coaches = [];

    for (const t of trainings || []) {
      const type = getText(t, ["type", "type_name", "training_type", "kind", "category", "format"]);
      const level = getText(t, ["level_name", "min_level_name", "max_level_name", "level", "level_title"]);
      const loc = getText(t, ["location.name", "location.title", "location.address", "location_name", "address"]);
      const coach = getText(t, ["coach_name", "trainer_name", "coach", "trainer", "instructor"]);

      if (type) types.push(type);
      if (level) levels.push(level);
      if (loc) locations.push(loc);
      if (coach) coaches.push(coach);
    }

    return {
      types: uniq(types),
      levels: uniq(levels),
      locations: uniq(locations),
      coaches: uniq(coaches),
    };
  }, [trainings]);

  const filtered = useMemo(() => {
    const list = trainings || [];

    return list.filter((t) => {
      const start = t.start_at ?? t.starts_at ?? null;
      if (start && !sameLocalDay(start, selectedDate)) return false;

      const type = getText(t, ["type", "type_name", "training_type", "kind", "category", "format"]);
      const level = getText(t, ["level_name", "min_level_name", "max_level_name", "level", "level_title"]);
      const loc = getText(t, ["location.name", "location.title", "location.address", "location_name", "address"]);
      const coach = getText(t, ["coach_name", "trainer_name", "coach", "trainer", "instructor"]);

      if (filters.types.length && !filters.types.some((x) => normalize(x) === normalize(type))) return false;
      if (filters.levels.length && !filters.levels.some((x) => normalize(x) === normalize(level))) return false;
      if (filters.locations.length && !filters.locations.some((x) => normalize(x) === normalize(loc))) return false;
      if (filters.coaches.length && !filters.coaches.some((x) => normalize(x) === normalize(coach))) return false;

      return true;
    });
  }, [trainings, selectedDate, filters]);

  function toggleFilter(group, value) {
    setFilters((prev) => {
      const exists = prev[group].some((x) => normalize(x) === normalize(value));
      const next = exists ? prev[group].filter((x) => normalize(x) !== normalize(value)) : [...prev[group], value];
      return { ...prev, [group]: next };
    });
  }

  function applyAndReload(nextDate = selectedDate, nextFilters = filters) {
    const payload = {
      date: ymd(nextDate),
      types: nextFilters.types,
      levels: nextFilters.levels,
      locations: nextFilters.locations,
      coaches: nextFilters.coaches,
    };
    onRefresh?.(payload);
  }

  function onPickDay(d) {
    setSelectedDate(d);
    applyAndReload(d, filters);
  }

  function resetFilters() {
    const cleared = { types: [], levels: [], locations: [], coaches: [] };
    setFilters(cleared);
    applyAndReload(selectedDate, cleared);
  }

  const sub = useMemo(() => ruLongDate(selectedDate), [selectedDate]);

  return (
    <>
      {/* Week strip */}
      <div className="week-strip">
        {week.map((d) => {
          const isActive = sameLocalDay(d, selectedDate);
          const dayLabel = RU_WEEK[d.getDay()];
          const dayNum = d.getDate();
          return (
            <button
              key={ymd(d)}
              type="button"
              className={`week-day ${isActive ? "active" : ""}`}
              onClick={() => onPickDay(d)}
            >
              <span>{dayLabel}</span>
              <span className="date">{dayNum}</span>
            </button>
          );
        })}
      </div>

      <div className="subheading">{sub}</div>

      <div className="filters-bar">
        <button className="filters-btn" type="button" onClick={() => setFiltersOpen(true)}>
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M4 5h16M7 12h10M10 19h4" />
          </svg>
          Фильтры
        </button>
      </div>

      {loading ? (
        <div className="empty">Загрузка...</div>
      ) : error ? (
        <div className="empty">{error}</div>
      ) : filtered.length === 0 ? (
        <div className="empty">На выбранный день тренировок нет</div>
      ) : (
        filtered.map((t) => {
          const start = t.start_at ?? t.starts_at ?? null;
          const img =
            t.image_url ||
            t.image ||
            t.photo_url ||
            "https://images.pexels.com/photos/945471/pexels-photo-945471.jpeg?auto=compress&cs=tinysrgb&w=800";

          const title = t.title || "Тренировка";
          const loc = getText(t, ["location.address", "location.name", "location_name", "address"]) || "—";
          const coach = getText(t, ["coach_name", "trainer_name", "coach", "trainer"]) || "";
          const status = statusLabel(t.user_enrollment_status);

          return (
            <article
              key={t.id}
              className="session-card"
              onClick={() => onOpenTraining?.(t.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(ev) => {
                if (ev.key === "Enter" || ev.key === " ") onOpenTraining?.(t.id);
              }}
            >
              <div className="session-image" style={{ backgroundImage: `url("${img}")` }}>
                <div className="session-time-pill">{ruTime(start)}</div>
                <div className={`status-pill ${status.kind}`}>{status.text}</div>
              </div>

              <div className="session-body">
                <div className="session-title-row">
                  <div className="session-title">{title}</div>
                  {coach ? <div className="session-trainer-pill">{coach}</div> : null}
                </div>
                <div className="session-location">{loc}</div>
                <div className="session-footer">
                  <span>
                    {t.capacity_main ?? t.capacity ?? "—"} мест · свободно {t.free_places ?? "—"}
                  </span>
                </div>
              </div>
            </article>
          );
        })
      )}

      {/* Filters modal */}
      <div
        className={`modal-backdrop ${filtersOpen ? "active" : ""}`}
        onClick={(e) => {
          if (e.target === e.currentTarget) setFiltersOpen(false);
        }}
      >
        <div className="modal">
          <div className="modal-title">Фильтры</div>
          <div className="modal-text">Выбери параметры и нажми “Применить”.</div>

          <div className="filters-section">
            <div className="filters-section-title">Тип</div>
            {options.types.length ? (
              options.types.map((v) => (
                <div key={v} className="filter-option" onClick={() => toggleFilter("types", v)} role="button" tabIndex={0}>
                  <span>{v}</span>
                  <div className={`checkbox ${filters.types.some((x) => normalize(x) === normalize(v)) ? "checked" : ""}`}>
                    {filters.types.some((x) => normalize(x) === normalize(v)) ? "✓" : ""}
                  </div>
                </div>
              ))
            ) : (
              <div className="muted" style={{ padding: "6px 0" }}>Нет данных</div>
            )}
          </div>

          <div className="filters-section">
            <div className="filters-section-title">Уровень</div>
            {options.levels.length ? (
              options.levels.map((v) => (
                <div key={v} className="filter-option" onClick={() => toggleFilter("levels", v)} role="button" tabIndex={0}>
                  <span>{v}</span>
                  <div className={`checkbox ${filters.levels.some((x) => normalize(x) === normalize(v)) ? "checked" : ""}`}>
                    {filters.levels.some((x) => normalize(x) === normalize(v)) ? "✓" : ""}
                  </div>
                </div>
              ))
            ) : (
              <div className="muted" style={{ padding: "6px 0" }}>Нет данных</div>
            )}
          </div>

          <div className="filters-section">
            <div className="filters-section-title">Локация</div>
            {options.locations.length ? (
              options.locations.map((v) => (
                <div key={v} className="filter-option" onClick={() => toggleFilter("locations", v)} role="button" tabIndex={0}>
                  <span>{v}</span>
                  <div className={`checkbox ${filters.locations.some((x) => normalize(x) === normalize(v)) ? "checked" : ""}`}>
                    {filters.locations.some((x) => normalize(x) === normalize(v)) ? "✓" : ""}
                  </div>
                </div>
              ))
            ) : (
              <div className="muted" style={{ padding: "6px 0" }}>Нет данных</div>
            )}
          </div>

          <div className="filters-section">
            <div className="filters-section-title">Тренер</div>
            {options.coaches.length ? (
              options.coaches.map((v) => (
                <div key={v} className="filter-option" onClick={() => toggleFilter("coaches", v)} role="button" tabIndex={0}>
                  <span>{v}</span>
                  <div className={`checkbox ${filters.coaches.some((x) => normalize(x) === normalize(v)) ? "checked" : ""}`}>
                    {filters.coaches.some((x) => normalize(x) === normalize(v)) ? "✓" : ""}
                  </div>
                </div>
              ))
            ) : (
              <div className="muted" style={{ padding: "6px 0" }}>Нет данных</div>
            )}
          </div>

          <div className="modal-actions">
            <button
              className="primary-btn"
              type="button"
              onClick={() => {
                setFiltersOpen(false);
                applyAndReload(selectedDate, filters);
              }}
            >
              Применить
            </button>

            <button className="ghost-btn" type="button" onClick={resetFilters}>
              Сбросить
            </button>

            <button className="ghost-btn" type="button" onClick={() => setFiltersOpen(false)}>
              Закрыть
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
