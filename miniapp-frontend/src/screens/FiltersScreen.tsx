import React, { useEffect, useMemo, useState } from "react";
import { useAppStore } from "../state/appStore";
import type { FiltersState } from "../types";

function cloneFilters(f: FiltersState): FiltersState {
  return {
    type: new Set(Array.from(f.type)),
    level: new Set(Array.from(f.level)),
    location: new Set(Array.from(f.location)),
  };
}

function ToggleRow(props: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={props.onClick}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 0",
        cursor: "pointer",
        gap: 12,
      }}
    >
      <span style={{ fontSize: 13 }}>{props.label}</span>
      <div
        style={{
          width: 20,
          height: 20,
          borderRadius: 6,
          border: "1.5px solid #d1d5db",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: props.active ? "var(--primary)" : "#fff",
          color: props.active ? "#fff" : "transparent",
          userSelect: "none",
          flexShrink: 0,
        }}
      >
        ✓
      </div>
    </div>
  );
}

export function FiltersScreen(props: { onBack: () => void; onApply: () => void }) {
  const store = useAppStore();
  const [draft, setDraft] = useState<FiltersState>(() => cloneFilters(store.filters));

  useEffect(() => {
    // каждый раз когда открыли экран — синхронизируем черновик
    setDraft(cloneFilters(store.filters));
  }, [store.filters]);

  const typeOptions = useMemo(() => ["Классика", "Турнир", "Баскетбол"], []);
  const levelOptions = useMemo(() => ["Новичок", "Средний-", "Средний", "Средний+"], []);
  const locationOptions = store.locationOptions; // подгрузим в Home при старте/смене недели

  function toggle(setKey: keyof FiltersState, value: string) {
    setDraft((prev) => {
      const next = cloneFilters(prev);
      const set = next[setKey];
      if (set.has(value)) set.delete(value);
      else set.add(value);
      return next;
    });
  }

  function reset() {
    setDraft({
      type: new Set(),
      level: new Set(),
      location: new Set(),
    });
  }

  function apply() {
    store.setFilters(draft);
    props.onApply();
  }

  return (
    <div className="screen active" style={{ padding: "16px 16px 90px" }}>
      <div className="back-row" style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <button className="back-btn" onClick={props.onBack} type="button">
          ←
        </button>
        <h2 className="topbar-title" style={{ fontSize: 22 }}>Фильтры</h2>
      </div>

      <div className="filters-section">
        <div className="filters-section-title">Тип тренировки</div>
        {typeOptions.map((v) => (
          <ToggleRow
            key={v}
            label={v}
            active={draft.type.has(v)}
            onClick={() => toggle("type", v)}
          />
        ))}
      </div>

      <div className="filters-section">
        <div className="filters-section-title">Уровень допуска</div>
        {levelOptions.map((v) => (
          <ToggleRow
            key={v}
            label={v}
            active={draft.level.has(v)}
            onClick={() => toggle("level", v)}
          />
        ))}
      </div>

      <div className="filters-section">
        <div className="filters-section-title">Место проведения</div>

        {locationOptions.length === 0 ? (
          <div style={{ fontSize: 13, color: "var(--text-muted)", padding: "6px 0" }}>
            Локации пока не загружены (появятся, когда есть тренировки)
          </div>
        ) : (
          locationOptions.map((loc) => (
            <ToggleRow
              key={loc.key}
              label={loc.title}
              active={draft.location.has(loc.key)}
              onClick={() => toggle("location", loc.key)}
            />
          ))
        )}
      </div>

      <div className="filter-footer" style={{ position: "sticky", bottom: 80, marginTop: 6 }}>
        <button className="secondary-btn" onClick={apply} type="button">
          Применить фильтры
        </button>
        <button className="ghost-btn" onClick={reset} type="button">
          Сбросить
        </button>
      </div>
    </div>
  );
}
