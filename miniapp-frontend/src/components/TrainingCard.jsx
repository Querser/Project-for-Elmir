import React, { useMemo } from 'react';

function num(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export default function TrainingCard({ training, onClick, timeLabel }) {
  const img =
    training?.image_url ||
    'https://images.unsplash.com/photo-1521412644187-c49fa049e84d?auto=format&fit=crop&w=1200&q=60';

  const minLv = training?.min_level_name ?? null;
  const maxLv = training?.max_level_name ?? null;
  const levels = [minLv, maxLv].filter(Boolean);

  const total = useMemo(() => num(training?.capacity_main) ?? 0, [training]);
  const free = useMemo(() => {
    const f = num(training?.free_places);
    if (f != null) return f;
    const occ = num(training?.occupied_main) ?? 0;
    const l = total - occ;
    return l >= 0 ? l : 0;
  }, [training, total]);

  const tag = training?.coach_name ? 'с тренером' : null;

  return (
    <article className="session-card" onClick={onClick} role="button" tabIndex={0}>
      <div className="session-image" style={{ backgroundImage: `url(${img})` }}>
        <div className="session-time-pill">{timeLabel}</div>
        <div className="session-chip-row">
          {levels.map((lvl, i) => (
             <span key={i} className="session-chip chip-level-light">{lvl}</span>
          ))}
        </div>
      </div>

      <div className="session-body">
        <div className="session-title-row">
          <div className="session-title">{training?.title || 'Тренировка'}</div>
          {tag && <div className="session-trainer-pill">{tag}</div>}
        </div>

        <div className="session-location">{training?.location || 'Локация уточняется'}</div>

        <div className="session-footer">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M5 12l3-3M5 12l3 3"/>
          </svg>
          <span>{total} мест всего · свободно {free}</span>
        </div>
      </div>
    </article>
  );
}