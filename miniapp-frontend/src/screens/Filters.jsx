import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api';
import RefreshButton from '../components/RefreshButton';

const TRAININGS_PAGE_LIMIT = 200;
const TRAININGS_MAX_PAGES = 30;
const SCHEDULE_DAYS_BACK = 31;
const SCHEDULE_DAYS_FORWARD = 180;

function normalizeItems(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.results)) return data.results;
  return [];
}

function uniqueSorted(arr) {
  return Array.from(new Set(arr.filter(Boolean))).sort((a, b) => String(a).localeCompare(String(b), 'ru'));
}

function toggle(arr, value) {
  const set = new Set(arr || []);
  if (set.has(value)) set.delete(value);
  else set.add(value);
  return Array.from(set);
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

function defaultDraft(initialFilters) {
  return {
    locationIds: initialFilters?.locationIds ?? [],
    coachNames: initialFilters?.coachNames ?? [],
    levelNames: initialFilters?.levelNames ?? [],
    kinds: initialFilters?.kinds ?? [],
    types: initialFilters?.types ?? [],
    startTimeFrom: initialFilters?.startTimeFrom ?? '',
    startTimeTo: initialFilters?.startTimeTo ?? '',
  };
}

export default function Filters({ initialFilters, onApply, onBack }) {
  const [draft, setDraft] = useState(() => defaultDraft(initialFilters));

  const [locations, setLocations] = useState([]);
  const [levels, setLevels] = useState([]);
  const [coaches, setCoaches] = useState([]);
  const [kinds, setKinds] = useState([]);
  const [types, setTypes] = useState([]);

  const [loading, setLoading] = useState(true);
  const [reloadTick, setReloadTick] = useState(0);

  const dateRange = useMemo(() => {
    const today = startOfDay(new Date());
    const from = addDays(today, -SCHEDULE_DAYS_BACK);
    const to = addDays(today, SCHEDULE_DAYS_FORWARD);
    return {
      fromIso: from.toISOString(),
      toIso: addDays(startOfDay(to), 1).toISOString(),
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setLoading(true);

        const [locRes, lvlRes] = await Promise.allSettled([
          apiFetch('/api/v1/locations?limit=500&offset=0&only_with_trainings=true'),
          apiFetch('/api/v1/levels'),
        ]);

        if (cancelled) return;

        if (locRes.status === 'fulfilled') {
          setLocations(normalizeItems(locRes.value));
        }

        if (lvlRes.status === 'fulfilled') {
          setLevels(normalizeItems(lvlRes.value));
        }

        const allTrainings = [];
        let offset = 0;
        let total = null;

        for (let page = 0; page < TRAININGS_MAX_PAGES; page += 1) {
          const params = new URLSearchParams();
          params.set('skip', String(offset));
          params.set('limit', String(TRAININGS_PAGE_LIMIT));
          params.set('date_from', dateRange.fromIso);
          params.set('date_to', dateRange.toIso);

          const trRes = await apiFetch(`/api/v1/trainings?${params.toString()}`);
          const items = normalizeItems(trRes);

          const apiTotal = Number(trRes?.total);
          if (Number.isFinite(apiTotal) && apiTotal >= 0) {
            total = apiTotal;
          }

          if (!items.length) break;
          allTrainings.push(...items);
          offset += items.length;

          if (total != null && offset >= total) break;
          if (items.length < TRAININGS_PAGE_LIMIT && total == null) break;
        }

        if (cancelled) return;

        setCoaches(uniqueSorted(allTrainings.map((t) => (t?.coach_name ?? '').trim()).filter(Boolean)));
        setKinds(uniqueSorted(allTrainings.map((t) => (t?.title ?? '').trim()).filter(Boolean)));

        const rawTypes = allTrainings
          .map((t) => (t?.type ?? t?.format ?? '').trim())
          .filter(Boolean);
        setTypes(uniqueSorted(rawTypes));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [dateRange.fromIso, dateRange.toIso, reloadTick]);

  const viewKinds = useMemo(() => kinds.slice(0, 8), [kinds]);
  const viewCoaches = useMemo(() => coaches.slice(0, 12), [coaches]);
  const viewLocations = useMemo(() => locations.slice(0, 25), [locations]);
  const viewLevels = useMemo(() => levels.slice(0, 30), [levels]);

  return (
    <>
      <header className="topbar">
        <button type="button" className="back-btn" onClick={onBack} aria-label="Назад">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <h1 className="topbar-title">Фильтры</h1>
        <RefreshButton onClick={() => setReloadTick((prev) => prev + 1)} />
      </header>

      <div className="content">
        {loading ? <div className="loader">Загрузка…</div> : null}

        <div className="filters-section">
          <h2>Вид тренировки</h2>
          <div className="filters-panel">
            {viewKinds.length ? (
              viewKinds.map((k) => (
                <label key={k} className="filter-option">
                  <span>{k}</span>
                  <input
                    type="checkbox"
                    checked={draft.kinds.includes(k)}
                    onChange={() => setDraft((s) => ({ ...s, kinds: toggle(s.kinds, k) }))}
                  />
                  <span className="checkbox" />
                </label>
              ))
            ) : (
              <div className="empty-state" style={{ margin: 0, padding: 14 }}>
                <p>Нет данных для фильтра по виду тренировки.</p>
              </div>
            )}
          </div>
        </div>

        {types.length ? (
          <div className="filters-section">
            <h2>Тип тренировки</h2>
            <div className="filters-panel">
              {types.map((t) => (
                <label key={t} className="filter-option">
                  <span>{t}</span>
                  <input
                    type="checkbox"
                    checked={draft.types.includes(t)}
                    onChange={() => setDraft((s) => ({ ...s, types: toggle(s.types, t) }))}
                  />
                  <span className="checkbox" />
                </label>
              ))}
            </div>
          </div>
        ) : null}

        <div className="filters-section">
          <h2>Локация</h2>
          <div className="filters-panel">
            {viewLocations.length ? (
              viewLocations.map((loc) => {
                const id = loc?.id ?? loc?.location_id ?? loc?.locationId ?? null;
                const label = loc?.name ?? loc?.title ?? loc?.address ?? `Локация #${id ?? ''}`;
                if (id == null) return null;

                return (
                  <label key={id} className="filter-option">
                    <span>{label}</span>
                    <input
                      type="checkbox"
                      checked={draft.locationIds.includes(id)}
                      onChange={() => setDraft((s) => ({ ...s, locationIds: toggle(s.locationIds, id) }))}
                    />
                    <span className="checkbox" />
                  </label>
                );
              })
            ) : (
              <div className="empty-state" style={{ margin: 0, padding: 14 }}>
                <p>Локации не найдены.</p>
              </div>
            )}
          </div>
        </div>

        <div className="filters-section">
          <h2>Тренер</h2>
          <div className="filters-panel">
            {viewCoaches.length ? (
              viewCoaches.map((c) => (
                <label key={c} className="filter-option">
                  <span>{c}</span>
                  <input
                    type="checkbox"
                    checked={draft.coachNames.includes(c)}
                    onChange={() => setDraft((s) => ({ ...s, coachNames: toggle(s.coachNames, c) }))}
                  />
                  <span className="checkbox" />
                </label>
              ))
            ) : (
              <div className="empty-state" style={{ margin: 0, padding: 14 }}>
                <p>Тренеры не найдены.</p>
              </div>
            )}
          </div>
        </div>

        <div className="filters-section">
          <h2>Уровень тренировки</h2>
          <div className="filters-panel">
            {viewLevels.length ? (
              viewLevels.map((lvl) => {
                const name = lvl?.name ?? lvl?.title ?? lvl?.level ?? null;
                if (!name) return null;
                return (
                  <label key={name} className="filter-option">
                    <span>{name}</span>
                    <input
                      type="checkbox"
                      checked={draft.levelNames.includes(name)}
                      onChange={() => setDraft((s) => ({ ...s, levelNames: toggle(s.levelNames, name) }))}
                    />
                    <span className="checkbox" />
                  </label>
                );
              })
            ) : (
              <div className="empty-state" style={{ margin: 0, padding: 14 }}>
                <p>Уровни не найдены.</p>
              </div>
            )}
          </div>
        </div>

        <div className="filters-section">
          <h2>Время начала тренировки</h2>
          <div className="filters-panel" style={{ gap: 10 }}>
            <label className="field" style={{ margin: 0 }}>
              <div className="field-label">С</div>
              <input
                type="time"
                className="input"
                value={draft.startTimeFrom}
                onChange={(ev) => setDraft((s) => ({ ...s, startTimeFrom: ev.target.value }))}
              />
            </label>

            <label className="field" style={{ margin: 0 }}>
              <div className="field-label">По</div>
              <input
                type="time"
                className="input"
                value={draft.startTimeTo}
                onChange={(ev) => setDraft((s) => ({ ...s, startTimeTo: ev.target.value }))}
              />
            </label>
          </div>
        </div>

        <div className="actions" style={{ marginTop: 14 }}>
          <button
            type="button"
            className="secondary-btn"
            onClick={() => setDraft(defaultDraft({}))}
          >
            Сбросить
          </button>

          <button type="button" className="primary-btn" onClick={() => onApply?.(draft)}>
            Применить фильтры
          </button>
        </div>
      </div>
    </>
  );
}