// src/screens/Notifications.jsx
import { useEffect, useState } from "react";
import { apiGet, extractItems } from "../api";
import DevAuth from "../components/DevAuth";

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [offset, setOffset] = useState(0);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load(reset = false) {
    setLoading(true);
    setError("");
    try {
      const lim = 30;
      const off = reset ? 0 : offset;
      const res = await apiGet(`/api/v1/notifications?limit=${lim}&offset=${off}`);
      const next = extractItems(res);

      setItems((prev) => (reset ? next : [...prev, ...next]));
      setOffset(off + lim);
    } catch (e) {
      console.error(e);
      if (e?.status === 401) {
        setError("401: требуется Telegram initData или dev-хедер X-User-Id/X-Telegram-Id.");
      } else {
        setError("Не удалось загрузить уведомления.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="screen">
      {error?.includes("401") ? <DevAuth onSaved={() => load(true)} /> : null}

      <div className="screen-actions">
        <button className="btn" onClick={() => load(true)} disabled={loading}>
          Обновить
        </button>
      </div>

      {loading && items.length === 0 ? (
        <div className="empty">Загрузка...</div>
      ) : error && items.length === 0 ? (
        <div className="empty">{error}</div>
      ) : items.length === 0 ? (
        <div className="empty">У вас ещё нет уведомлений</div>
      ) : (
        <>
          {items.map((n) => (
            <div className="card" key={n.id}>
              <div className="card-title">{n.title ?? "Уведомление"}</div>
              <div className="muted">{n.text ?? n.message ?? ""}</div>
              {n.url ? (
                <button
                  className="btn btn-ghost"
                  onClick={() => window.open(n.url, "_blank", "noopener,noreferrer")}
                  style={{ marginTop: 10 }}
                >
                  Открыть
                </button>
              ) : null}
            </div>
          ))}

          <div className="screen-actions">
            <button className="btn btn-ghost" onClick={() => load(false)} disabled={loading}>
              {loading ? "Загрузка..." : "Показать ещё"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
