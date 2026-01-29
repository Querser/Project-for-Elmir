import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { apiGet, extractItems } from '../api';
import Schedule from './Schedule';
import TrainingDetail from './TrainingDetail';

const VIEW_HOME = 'home';
const VIEW_FILTERS = 'filters';
const VIEW_SESSION = 'session';

function IconBell() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}
function IconBack() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

export default function ScheduleTab({ active, onGoNotifications }) {
  const [view, setView] = useState(VIEW_HOME);

  const [trainings, setTrainings] = useState([]);
  const [locations, setLocations] = useState([]);
  const [levels, setLevels] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [filters, setFilters] = useState({ locationId: null, levelId: null });

  const [filtersDraft, setFiltersDraft] = useState({ locationId: null, levelId: null });

  const [detailTrainingId, setDetailTrainingId] = useState(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [trRes, locRes, levRes] = await Promise.all([
        apiGet('/api/v1/trainings?limit=200&offset=0'),
        apiGet('/api/v1/locations?limit=500&offset=0'),
        apiGet('/api/v1/levels?limit=200&offset=0'),
      ]);

      setTrainings(extractItems(trRes));
      setLocations(extractItems(locRes));
      setLevels(extractItems(levRes));
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (view === VIEW_FILTERS) setFiltersDraft(filters);
  }, [view, filters]);

  const isFiltersActive = useMemo(() => !!(filters.locationId || filters.levelId), [filters]);

  function openFilters() {
    setView(VIEW_FILTERS);
  }
  function closeFilters(apply) {
    if (apply) setFilters(filtersDraft);
    setView(VIEW_HOME);
  }
  function openTraining(id) {
    setDetailTrainingId(id);
    setView(VIEW_SESSION);
  }
  function closeTraining() {
    setDetailTrainingId(null);
    setView(VIEW_HOME);
  }

  return (
    <>
      {/* HOME / Schedule */}
      <section className={`screen ${active && view === VIEW_HOME ? 'active' : ''}`} id="screen-home">
        <div className="topbar">
          <div className="title">Расписание</div>
          <button className="icon-btn" onClick={onGoNotifications} aria-label="Уведомления">
            <IconBell />
          </button>
        </div>

        {error ? <div className="toast error">{error}</div> : null}

        {loading ? (
          <div className="empty">Загрузка расписания…</div>
        ) : (
          <Schedule
            trainings={trainings}
            locations={locations}
            levels={levels}
            filters={filters}
            onOpenFilters={openFilters}
            onSelectTraining={openTraining}
            showFiltersBadge={isFiltersActive}
          />
        )}
      </section>

      {/* FILTERS */}
      <section className={`screen ${active && view === VIEW_FILTERS ? 'active' : ''}`} id="screen-filters">
        <div className="topbar">
          <button className="icon-btn" onClick={() => closeFilters(false)} aria-label="Назад">
            <IconBack />
          </button>
          <div className="title">Фильтры</div>
          <div style={{ width: 40 }} />
        </div>

        <div className="content">
          <div className="card">
            <div className="card-title">Локация</div>
            <div style={{ display: 'grid', gap: 8 }}>
              <label className="row" style={{ justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 800 }}>Все</span>
                <input
                  type="radio"
                  name="loc"
                  checked={!filtersDraft.locationId}
                  onChange={() => setFiltersDraft((s) => ({ ...s, locationId: null }))}
                />
              </label>

              {locations.map((l) => (
                <label key={l.id} className="row" style={{ justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 800 }}>{l.name || l.address || `Локация #${l.id}`}</span>
                  <input
                    type="radio"
                    name="loc"
                    checked={filtersDraft.locationId === l.id}
                    onChange={() => setFiltersDraft((s) => ({ ...s, locationId: l.id }))}
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-title">Уровень</div>
            <div style={{ display: 'grid', gap: 8 }}>
              <label className="row" style={{ justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 800 }}>Все</span>
                <input
                  type="radio"
                  name="lvl"
                  checked={!filtersDraft.levelId}
                  onChange={() => setFiltersDraft((s) => ({ ...s, levelId: null }))}
                />
              </label>

              {levels.map((lvl) => (
                <label key={lvl.id} className="row" style={{ justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 800 }}>{lvl.name || `Уровень #${lvl.id}`}</span>
                  <input
                    type="radio"
                    name="lvl"
                    checked={filtersDraft.levelId === lvl.id}
                    onChange={() => setFiltersDraft((s) => ({ ...s, levelId: lvl.id }))}
                  />
                </label>
              ))}
            </div>
          </div>

          <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => closeFilters(true)}>
            Применить
          </button>
        </div>
      </section>

      {/* SESSION DETAILS */}
      <section className={`screen ${active && view === VIEW_SESSION ? 'active' : ''}`} id="screen-session">
        <div className="topbar">
          <button className="icon-btn" onClick={closeTraining} aria-label="Назад">
            <IconBack />
          </button>
          <div className="title">Тренировка</div>
          <div style={{ width: 40 }} />
        </div>

        <div className="content">
          {detailTrainingId ? (
            <TrainingDetail
              trainingId={detailTrainingId}
              locations={locations}
              onChanged={loadAll}
            />
          ) : (
            <div className="empty">Не выбрана тренировка</div>
          )}
        </div>
      </section>
    </>
  );
}
