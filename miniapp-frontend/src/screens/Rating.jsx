// src/screens/Rating.jsx
import { useEffect, useState } from "react";
import { apiGet, extractItems } from "../api";

const LEVEL_HINTS = {
  "Beginner": "Новичок: базовые навыки, простые упражнения",
  "Intermediate": "Средний: стабильная техника, больше игры",
  "Advanced": "Продвинутый: высокая динамика и сложные задания",
};

export default function Rating({ onOpenUser }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await apiGet("/api/v1/ratings?limit=200&offset=0");
      setItems(extractItems(res));
    } catch (e) {
      console.error(e);
      setItems([]);
      setError("Не удалось загрузить рейтинг (проверь /api/v1/ratings).");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <section className="screen">
      <div className="screen-actions">
        <button className="btn" onClick={load}>Обновить</button>
      </div>

      {loading ? (
        <div className="empty">Загрузка...</div>
      ) : error ? (
        <div className="empty">{error}</div>
      ) : items.length === 0 ? (
        <div className="empty">Рейтинг пуст</div>
      ) : (
        items.map((p, idx) => {
          const place = p.place ?? idx + 1;
          const levelName = p.level_name ?? p.level_title ?? "—";
          const hint = LEVEL_HINTS[levelName] || "";
          return (
            <button
              className="card card-button"
              key={p.user_id ?? p.id ?? idx}
              onClick={() => onOpenUser?.(p.user_id)}
            >
              <div className="card-title">
                {place}. {p.first_name || ""} {p.last_name || ""}{" "}
                {p.username ? `(@${p.username})` : ""}
              </div>
              <div className="muted">
                Очки: {p.rating ?? p.avg_score ?? "—"} • Кубки: {p.cups ?? "—"}
              </div>
              <div className="muted" title={hint}>
                Уровень: {levelName}
                {hint ? " (наведи)" : ""}
              </div>
            </button>
          );
        })
      )}
    </section>
  );
}
