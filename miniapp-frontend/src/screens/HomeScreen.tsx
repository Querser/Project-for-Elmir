import React, { useEffect } from "react";
import { useAppStore } from "../state/appStore";
import { formatHomeHeading, getMonday, ruWeekdayShort, sameDay } from "../lib/date";
import { loadLocationsUniversal, loadTrainings } from "../lib/trainings";

export function HomeScreen(props: { onOpenFilters: () => void }) {
  const store = useAppStore();

  async function refreshTrainings() {
    try {
      const list = await loadTrainings({
        token: store.token,
        date: store.selectedDate,
        filters: store.filters,
      });
      store.setTrainings(list);
    } catch {
      store.setTrainings([]);
    }
  }

  async function refreshLocationsForWeek() {
    try {
      const locs = await loadLocationsUniversal({
        token: store.token,
        dateInWeek: store.selectedDate,
      });
      store.setLocationOptions(locs);
    } catch {
      store.setLocationOptions([]);
    }
  }

  useEffect(() => {
    refreshTrainings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store.selectedDate, store.filters, store.token]);

  useEffect(() => {
    // обновляем локации когда меняется неделя (понедельник недели)
    const monday = getMonday(store.selectedDate).getTime();
    void monday;
    refreshLocationsForWeek();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [getMonday(store.selectedDate).getTime(), store.token]);

  const monday = getMonday(store.selectedDate);
  const days = Array.from({ length: 7 }).map((_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });

  return (
    <div style={{ padding: "16px 16px 90px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0 }}>Расписание</h1>
        <button
          type="button"
          style={{
            width: 40,
            height: 40,
            borderRadius: 999,
            border: "none",
            cursor: "pointer",
            background: "var(--bg-alt, #fff)",
          }}
          title="На весь экран"
        >
          ⤢
        </button>
      </div>

      <div style={{ display: "flex", gap: 10, overflowX: "auto", paddingBottom: 6, marginBottom: 8 }}>
        {days.map((d) => (
          <div
            key={d.toISOString()}
            onClick={() => store.setSelectedDate(d)}
            style={{
              minWidth: 56,
              height: 72,
              borderRadius: 999,
              background: sameDay(d, store.selectedDate) ? "var(--primary, #2f7df6)" : "var(--bg-alt, #fff)",
              color: sameDay(d, store.selectedDate) ? "#fff" : "var(--text-muted, #6b7280)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              userSelect: "none",
              flexShrink: 0,
            }}
          >
            <span>{ruWeekdayShort(d)}</span>
            <span style={{ fontSize: 18, fontWeight: 600, marginTop: 4, color: sameDay(d, store.selectedDate) ? "#fff" : "var(--text-main, #111827)" }}>
              {d.getDate()}
            </span>
          </div>
        ))}
      </div>

      <p style={{ margin: "8px 0 10px", fontSize: 16, fontWeight: 600 }}>
        {formatHomeHeading(store.selectedDate, store.city)}
      </p>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10, marginBottom: 6 }}>
        <button
          type="button"
          onClick={props.onOpenFilters}
          style={{
            padding: "8px 14px",
            borderRadius: 999,
            border: "none",
            background: "var(--primary, #2f7df6)",
            color: "#fff",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          Фильтры
        </button>
      </div>

      <div>
        {store.trainings.length === 0 ? (
          <p style={{ marginTop: 28, textAlign: "center", color: "var(--text-muted, #6b7280)" }}>
            На этот день расписания нет
          </p>
        ) : (
          store.trainings.map((t) => (
            <div
              key={String(t.id)}
              style={{
                background: "var(--bg-alt, #fff)",
                borderRadius: 16,
                padding: 12,
                marginBottom: 10,
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 14 }}>{t.title}</div>
              <div style={{ fontSize: 13, color: "var(--text-muted, #6b7280)", marginTop: 4 }}>
                {t.time} · {t.locationDisplay}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted, #6b7280)", marginTop: 4 }}>
                {t.occupied}/{t.capacity} занято · свободно {t.free}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
