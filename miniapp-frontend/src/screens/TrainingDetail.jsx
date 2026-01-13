// src/screens/TrainingDetail.jsx
import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost, openCalendar } from "../api";

function toRuDateTime(dt) {
  if (!dt) return "—";
  try {
    return new Date(dt).toLocaleString("ru-RU");
  } catch {
    return String(dt);
  }
}

function getErrorText(e) {
  const msg = e?.message || "Ошибка";
  const backendMsg = e?.data?.error?.message || e?.data?.detail;
  return backendMsg || msg;
}

/**
 * ВАЖНО:
 * Компонент рендерит только "контент" (карточки), без собственного topbar/tabbar,
 * чтобы внешний вид оставался как в твоём исходном App.jsx.
 */
export default function TrainingDetail({ trainingId, onChanged }) {
  const [t, setT] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await apiGet(`/api/v1/trainings/${trainingId}`);
      const tt = res?.result ? res.result : res;
      setT(tt);
    } catch (e) {
      console.error(e);
      setT(null);
      setError(getErrorText(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trainingId]);

  const status = String(t?.user_enrollment_status || "none").toLowerCase();
  const canCancel =
    status === "main" ||
    status === "reserve" ||
    status === "enrolled" ||
    status === "booked" ||
    status === "waitlist";
  const canEnroll = !canCancel && status !== "not_allowed" && status !== "forbidden";

  async function enroll() {
    setBusy(true);
    setError("");
    try {
      try {
        await apiPost(`/api/v1/trainings/${trainingId}/enroll`, {});
      } catch {
        // fallback — если у тебя другой endpoint
        await apiPost(`/api/v1/enrollments`, { training_id: trainingId });
      }
      await load();
      onChanged?.();
    } catch (e) {
      console.error(e);
      setError(getErrorText(e));
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    setBusy(true);
    setError("");
    try {
      try {
        await apiDelete(`/api/v1/trainings/${trainingId}/enroll`);
      } catch {
        // fallback — если у тебя другой endpoint
        await apiPost(`/api/v1/enrollments/cancel`, { training_id: trainingId });
      }
      await load();
      onChanged?.();
    } catch (e) {
      console.error(e);
      setError(getErrorText(e));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="empty">Загрузка...</div>;
  if (error && !t) return <div className="empty">{error}</div>;
  if (!t) return <div className="empty">Тренировка не найдена</div>;

  const start = t.start_at ?? t.starts_at ?? null;

  const main = t.main || t.main_list || t.roster_main || t.enrollments_main || [];
  const reserve = t.reserve || t.reserve_list || t.roster_reserve || t.enrollments_reserve || [];
  const allEnrollments = t.enrollments || [];

  const locationUrl =
    t.maps_url ||
    t.location?.maps_url ||
    t.location?.mapsUrl ||
    t.location?.map_url ||
    null;

  const howToVideo =
    t.video_url ||
    t.location?.video_url ||
    t.location?.videoUrl ||
    null;

  const actionBtn = (primary = false) => ({
    width: "100%",
    padding: "10px 12px",
    borderRadius: 14,
    border: primary ? "none" : "1px solid rgba(0,0,0,0.12)",
    background: primary ? "#2f7df6" : "transparent",
    color: primary ? "#fff" : "#2f7df6",
    fontWeight: 700,
    cursor: "pointer",
  });

  return (
    <>
      <div className="card">
        <div className="card-title">{t.title || "Тренировка"}</div>
        <div className="muted">Старт: {toRuDateTime(start)}</div>
        <div className="muted">Длительность: {t.duration_minutes ?? "—"} мин</div>
        <div className="muted">Свободно мест: {t.free_places ?? "—"}</div>
        <div className="muted">Статус: {t.user_enrollment_status || "none"}</div>

        {error ? <div className="muted" style={{ color: "#ef4444", fontWeight: 600, marginTop: 10 }}>{error}</div> : null}

        <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
          {canEnroll ? (
            <button style={actionBtn(true)} disabled={busy} onClick={enroll}>
              Записаться
            </button>
          ) : null}

          {canCancel ? (
            <button style={actionBtn(false)} disabled={busy} onClick={cancel}>
              Отменить запись
            </button>
          ) : null}

          {locationUrl ? (
            <button
              style={actionBtn(false)}
              onClick={() => window.open(locationUrl, "_blank", "noopener,noreferrer")}
            >
              Открыть карту
            </button>
          ) : null}

          {howToVideo ? (
            <button
              style={actionBtn(false)}
              onClick={() => window.open(howToVideo, "_blank", "noopener,noreferrer")}
            >
              Как пройти (видео)
            </button>
          ) : null}

          <button
            style={actionBtn(false)}
            onClick={async () => {
              try {
                await openCalendar(trainingId);
              } catch (e) {
                setError(e?.message || "Не удалось открыть календарь");
              }
            }}
          >
            Добавить в календарь
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Состав</div>

        {Array.isArray(main) && main.length > 0 ? (
          <>
            <div className="muted" style={{ marginTop: 8, marginBottom: 6 }}>
              Основа
            </div>
            {main.map((p, idx) => (
              <div className="muted" key={p.user_id ?? p.id ?? idx} style={{ padding: "6px 0" }}>
                {(p.first_name || p.user_first_name || "Игрок") + " " + (p.last_name || "")}
                {p.username ? ` (@${p.username})` : ""}
              </div>
            ))}
          </>
        ) : null}

        {Array.isArray(reserve) && reserve.length > 0 ? (
          <>
            <div className="muted" style={{ marginTop: 12, marginBottom: 6 }}>
              Резерв
            </div>
            {reserve.map((p, idx) => (
              <div className="muted" key={p.user_id ?? p.id ?? idx} style={{ padding: "6px 0" }}>
                {(p.first_name || p.user_first_name || "Игрок") + " " + (p.last_name || "")}
                {p.username ? ` (@${p.username})` : ""}
              </div>
            ))}
          </>
        ) : null}

        {!main?.length && !reserve?.length && Array.isArray(allEnrollments) && allEnrollments.length > 0 ? (
          <>
            <div className="muted" style={{ marginTop: 12, marginBottom: 6 }}>
              Записи
            </div>
            {allEnrollments.map((e, idx) => (
              <div className="muted" key={e.id ?? idx} style={{ padding: "6px 0" }}>
                {(e.user?.first_name || e.first_name || "Игрок") +
                  " " +
                  (e.user?.last_name || e.last_name || "")}
                {e.status ? ` • ${e.status}` : ""}
              </div>
            ))}
          </>
        ) : null}

        {!main?.length && !reserve?.length && !allEnrollments?.length ? (
          <div className="empty" style={{ padding: 0 }}>
            Состав пока недоступен
          </div>
        ) : null}
      </div>
    </>
  );
}
