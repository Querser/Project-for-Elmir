import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiFetch } from '../api';
import RefreshButton from '../components/RefreshButton';
import TrainingCard from '../components/TrainingCard';

const TRAININGS_LIMIT = 200;
const LOCATIONS_LIMIT = 500;

function pad2(n) {
  return String(n).padStart(2, '0');
}

function dateKeyLocal(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function startOfDay(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function addDays(d, days) {
  const x = new Date(d);
  x.setDate(x.getDate() + days);
  return x;
}

function dateFromKey(key) {
  const m = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/.exec(String(key || ''));
  if (!m) return null;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const da = Number(m[3]);
  if (!Number.isFinite(y) || !Number.isFinite(mo) || !Number.isFinite(da)) return null;
  const dt = new Date(y, mo - 1, da);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function parseStartAt(t) {
  const raw = t?.starts_at ?? t?.start_at ?? t?.startsAt ?? t?.startAt ?? null;
  if (!raw) return null;
  const dt = new Date(raw);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function formatTime(dt) {
  return dt ? dt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '';
}

function capFirst(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function normalizeTrainingsResponse(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.results)) return data.results;
  return [];
}

function normalizeLocationsResponse(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.results)) return data.results;
  return [];
}

function normalizeLocationLabel(loc) {
  if (!loc) return '';
  const name = loc?.name ?? loc?.title ?? '';
  const address = loc?.address ?? loc?.addr ?? '';
  return String(name || address || '').trim();
}

function normalizeString(v) {
  if (v == null) return '';
  return String(v).trim().toLowerCase();
}

function normalizeId(v) {
  if (v == null) return '';
  const n = Number(v);
  return Number.isFinite(n) ? String(n) : String(v);
}

function getTrainingKind(t) {
  return (
    t?.kind ??
    t?.training_kind ??
    t?.trainingKind ??
    t?.category ??
    t?.training_category ??
    t?.trainingCategory ??
    t?.title ??
    ''
  );
}

function getTrainingType(t) {
  return (
    t?.type ??
    t?.training_type ??
    t?.trainingType ??
    t?.sport_type ??
    t?.sportType ??
    t?.format ??
    ''
  );
}

function getTrainingCoach(t) {
  return t?.coach_name ?? t?.coachName ?? t?.trainer ?? t?.trainer_name ?? t?.trainerName ?? '';
}

function getTrainingLocationId(t) {
  return t?.location_id ?? t?.locationId ?? t?.location?.id ?? '';
}

function getTrainingLevelNames(t) {
  const arr = [];

  const min = t?.min_level_name ?? t?.minLevelName ?? '';
  const max = t?.max_level_name ?? t?.maxLevelName ?? '';
  const single = t?.level_name ?? t?.levelName ?? '';
  const allowed = t?.allowed_levels ?? t?.allowedLevels ?? null;

  if (single) arr.push(single);
  if (min) arr.push(min);
  if (max) arr.push(max);

  if (Array.isArray(allowed)) {
    for (const x of allowed) {
      if (x) arr.push(String(x));
    }
  }

  const uniq = [];
  for (const x of arr) {
    const s = String(x).trim();
    if (!s) continue;
    if (!uniq.includes(s)) uniq.push(s);
  }
  return uniq;
}

function isFiltersEmpty(filters) {
  if (!filters) return true;
  const keys = ['kinds', 'types', 'locationIds', 'coachNames', 'levelNames'];
  return keys.every((k) => !Array.isArray(filters[k]) || filters[k].length === 0);
}

function applyFilters(trainings, filters) {
  if (!Array.isArray(trainings)) return [];
  if (isFiltersEmpty(filters)) return trainings;

  const wantedKinds = new Set((filters?.kinds || []).map(normalizeString).filter(Boolean));
  const wantedTypes = new Set((filters?.types || []).map(normalizeString).filter(Boolean));
  const wantedLocations = new Set((filters?.locationIds || []).map(normalizeId).filter(Boolean));
  const wantedCoaches = new Set((filters?.coachNames || []).map(normalizeString).filter(Boolean));
  const wantedLevels = new Set((filters?.levelNames || []).map(normalizeString).filter(Boolean));

  return trainings.filter((t) => {
    if (wantedKinds.size > 0) {
      const kind = normalizeString(getTrainingKind(t));
      if (!kind || !wantedKinds.has(kind)) return false;
    }

    if (wantedTypes.size > 0) {
      const type = normalizeString(getTrainingType(t));
      if (!type || !wantedTypes.has(type)) return false;
    }

    if (wantedLocations.size > 0) {
      const locId = normalizeId(getTrainingLocationId(t));
      if (!locId || !wantedLocations.has(locId)) return false;
    }

    if (wantedCoaches.size > 0) {
      const coach = normalizeString(getTrainingCoach(t));
      if (!coach || !wantedCoaches.has(coach)) return false;
    }

    if (wantedLevels.size > 0) {
      const levelNames = getTrainingLevelNames(t).map(normalizeString).filter(Boolean);
      const hit = levelNames.some((n) => wantedLevels.has(n));
      if (!hit) return false;
    }

    return true;
  });
}

function safeTrainingId(t) {
  return t?.id ?? t?.training_id ?? t?.trainingId ?? null;
}

export default function Schedule({
  filters,
  refreshKey,
  refreshTick,
  onOpenFilters,
  onOpenTraining,
}) {
  const [allTrainings, setAllTrainings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const today = useMemo(() => startOfDay(new Date()), []);
  const daysRange = useMemo(() => {
    const start = addDays(today, -31);
    return Array.from({ length: 63 }, (_, i) => addDays(start, i));
  }, [today]);

  const [selectedDay, setSelectedDay] = useState(() => dateKeyLocal(today));
  const weekStripRef = useRef(null);

  const effectiveRefresh = refreshTick ?? refreshKey ?? 0;

  const loadSchedule = useCallback(async () => {
    try {
      setLoading(true);
      setError('');

      const trData = await apiFetch(`/api/v1/trainings?skip=0&limit=${TRAININGS_LIMIT}`);
      const trainings = normalizeTrainingsResponse(trData);

      let locMap = {};
      try {
        const locData = await apiFetch(`/api/v1/locations?limit=${LOCATIONS_LIMIT}&offset=0&only_with_trainings=true`);
        const locItems = normalizeLocationsResponse(locData);

        const map = {};
        for (const loc of locItems) {
          const id = loc?.id ?? loc?.location_id ?? loc?.locationId ?? null;
          if (id == null) continue;
          const label = normalizeLocationLabel(loc);
          if (!map[String(id)]) map[String(id)] = label || '';
        }
        locMap = map;
      } catch (e) {
        void e;
      }

      const enriched = trainings.map((t) => {
        const locationId = getTrainingLocationId(t);
        const label = locationId ? (locMap[String(locationId)] || '') : '';

        const baseLocation =
          (t?.location ?? null) ??
          (t?.location_name ?? null) ??
          (t?.locationName ?? null) ??
          (t?.location_label ?? null) ??
          null;

        let locationText = '';
        if (baseLocation != null && String(baseLocation).trim() !== '') {
          locationText = String(baseLocation).trim();
        } else if (label && String(label).trim() !== '') {
          locationText = String(label).trim();
        }

        return {
          ...t,
          location_label: label,
          location: locationText,
        };
      });

      setAllTrainings(enriched);
    } catch (err) {
      setError(err?.message || 'Ошибка загрузки расписания');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSchedule();
  }, [effectiveRefresh, loadSchedule]);

  const trainingsFiltered = useMemo(() => applyFilters(allTrainings, filters), [allTrainings, filters]);

  const selectedTrainings = useMemo(() => {
    return trainingsFiltered
      .filter((t) => {
        const dt = parseStartAt(t);
        return dt && dateKeyLocal(dt) === selectedDay;
      })
      .sort((a, b) => (parseStartAt(a)?.getTime() || 0) - (parseStartAt(b)?.getTime() || 0));
  }, [trainingsFiltered, selectedDay]);

  const dayLabel = useMemo(() => {
    const found = daysRange.find((d) => dateKeyLocal(d) === selectedDay) || dateFromKey(selectedDay) || new Date();
    return capFirst(found.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }));
  }, [selectedDay, daysRange]);

  useEffect(() => {
    const root = weekStripRef.current;
    if (!root) return;
    const btn = root.querySelector(`[data-day="${selectedDay}"]`);
    if (btn && typeof btn.scrollIntoView === 'function') {
      btn.scrollIntoView({ block: 'nearest', inline: 'center' });
    }
  }, [selectedDay]);

  const activeFiltersCount = useMemo(() => {
    if (!filters) return 0;
    return ['kinds', 'types', 'locationIds', 'coachNames', 'levelNames'].reduce((acc, k) => {
      const v = filters[k];
      return acc + (Array.isArray(v) ? v.length : 0);
    }, 0);
  }, [filters]);

  return (
    <>
      <div className="topbar">
        <h1 className="topbar-title">Расписание</h1>
        <RefreshButton onClick={loadSchedule} />
      </div>

      <div className="week-strip" ref={weekStripRef}>
        {daysRange.map((d) => {
          const key = dateKeyLocal(d);
          const isSelected = key === selectedDay;
          return (
            <button
              key={key}
              type="button"
              className={`week-day ${isSelected ? 'active' : ''}`}
              onClick={() => setSelectedDay(key)}
              data-day={key}
            >
              <span>{d.toLocaleDateString('ru-RU', { weekday: 'short' }).toUpperCase()}</span>
              <span className="date">{d.getDate()}</span>
            </button>
          );
        })}
      </div>

      <p className="subheading">{dayLabel} · Москва</p>

      <div className="filters-bar">
        <button className="filters-btn" type="button" onClick={onOpenFilters}>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 5h16M7 12h10M10 19h4" />
          </svg>
          Фильтры{activeFiltersCount > 0 ? ` (${activeFiltersCount})` : ''}
        </button>
      </div>

      {loading ? <div className="loader">Загрузка…</div> : null}

      {!loading && error ? (
        <div className="empty-state" style={{ marginTop: 18 }}>
          <div className="empty-ico">⚠️</div>
          <h3>Ошибка</h3>
          <p>{error}</p>
        </div>
      ) : null}

      {!loading && !error ? (
        <div id="sessions-list">
          {selectedTrainings.length === 0 ? (
            <div className="empty-state" style={{ marginTop: 18 }}>
              <div className="empty-ico">📅</div>
              <h3>Нет тренировок</h3>
              <p>В этот день тренировки не запланированы.</p>
            </div>
          ) : (
            selectedTrainings.map((t) => {
              const id = safeTrainingId(t);
              return (
                <TrainingCard
                  key={id ?? `${t?.title ?? 'training'}-${parseStartAt(t)?.toISOString() ?? ''}`}
                  training={t}
                  onClick={() => (id ? onOpenTraining?.(id) : null)}
                  timeLabel={formatTime(parseStartAt(t))}
                />
              );
            })
          )}
        </div>
      ) : null}
    </>
  );
}
