import { useEffect, useState } from "react";
import "./App.css";
import { apiGet, initMiniAppAuth } from "./api";

import Schedule from "./screens/Schedule";
import TrainingDetail from "./screens/TrainingDetail";
import Profile from "./screens/Profile";

function extractItems(res) {
  if (!res) return [];
  if (Array.isArray(res)) return res;
  if (Array.isArray(res.items)) return res.items;
  if (res.result && Array.isArray(res.result.items)) return res.result.items;
  return [];
}

function buildTrainingsUrl(params = {}) {
  const qs = new URLSearchParams();
  qs.set("limit", "200");
  qs.set("offset", "0");

  if (params.date) qs.set("date", params.date);

  // мульти-фильтры шлём как comma-separated (если backend не поддержит — будет fallback)
  const join = (a) => (Array.isArray(a) && a.length ? a.join(",") : "");
  if (join(params.types)) qs.set("type", join(params.types));
  if (join(params.levels)) qs.set("level", join(params.levels));
  if (join(params.locations)) qs.set("location", join(params.locations));
  if (join(params.coaches)) qs.set("coach", join(params.coaches));

  return `/api/v1/trainings?${qs.toString()}`;
}

const linkBtnStyle = {
  border: "none",
  background: "transparent",
  color: "#2f7df6",
  fontWeight: 600,
  cursor: "pointer",
};

export default function App() {
  const [tab, setTab] = useState("schedule");

  const [trainings, setTrainings] = useState([]);
  const [rating, setRating] = useState([]);
  const [notifications, setNotifications] = useState([]);

  const [loadingSchedule, setLoadingSchedule] = useState(false);
  const [loadingRating, setLoadingRating] = useState(false);
  const [loadingNotifs, setLoadingNotifs] = useState(false);

  const [errorSchedule, setErrorSchedule] = useState("");
  const [errorRating, setErrorRating] = useState("");
  const [errorNotifs, setErrorNotifs] = useState("");

  const [openTrainingId, setOpenTrainingId] = useState(null);
  const [openUserId, setOpenUserId] = useState(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    tg?.ready?.();
    tg?.expand?.();
    initMiniAppAuth();
  }, []);

  useEffect(() => {
    loadSchedule(); // первичная загрузка без фильтров (Schedule сам умеет дёргать refresh при выборе дня/фильтров)
    loadRating();
    loadNotifs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadSchedule(params = null) {
    setLoadingSchedule(true);
    setErrorSchedule("");
    try {
      // 1) пробуем с параметрами (date/filters)
      if (params) {
        const url = buildTrainingsUrl(params);
        try {
          const res = await apiGet(url);
          setTrainings(extractItems(res));
          return;
        } catch {
          // backend может не поддерживать эти query — fallback ниже
        }
      }

      // 2) fallback — без параметров
      const res = await apiGet("/api/v1/trainings?limit=200&offset=0");
      setTrainings(extractItems(res));
    } catch (e) {
      console.error(e);
      setTrainings([]);
      setErrorSchedule("Не удалось загрузить расписание (проверь backend и /api/v1/trainings).");
    } finally {
      setLoadingSchedule(false);
    }
  }

  async function loadRating() {
    setLoadingRating(true);
    setErrorRating("");
    try {
      const res = await apiGet("/api/v1/ratings?limit=200&offset=0");
      setRating(extractItems(res));
    } catch (e) {
      console.error(e);
      setRating([]);
      setErrorRating("Не удалось загрузить рейтинг (проверь /api/v1/ratings в backend).");
    } finally {
      setLoadingRating(false);
    }
  }

  async function loadNotifs() {
    setLoadingNotifs(true);
    setErrorNotifs("");
    try {
      const res = await apiGet("/api/v1/notifications?limit=50&offset=0");
      setNotifications(extractItems(res));
    } catch (e) {
      console.error(e);
      setNotifications([]);
      setErrorNotifs(
        "Не удалось загрузить уведомления. В браузере это обычно 401 без Telegram initData или X-User-Id/X-Telegram-Id."
      );
    } finally {
      setLoadingNotifs(false);
    }
  }

  function safeSetTab(next) {
    setOpenTrainingId(null);
    setOpenUserId(null);
    setTab(next);
  }

  return (
    <div className="app">
      <div className="content">
        {/* ====== РАСПИСАНИЕ ====== */}
        {tab === "schedule" && (
          <section className="screen">
            <div className="topbar">
              {openTrainingId ? (
                <button onClick={() => setOpenTrainingId(null)} style={linkBtnStyle}>
                  ← Назад
                </button>
              ) : (
                <h1 className="topbar-title">Расписание</h1>
              )}

              <button onClick={() => loadSchedule()} style={linkBtnStyle}>
                Обновить
              </button>
            </div>

            {openTrainingId ? (
              <TrainingDetail trainingId={openTrainingId} onChanged={() => loadSchedule()} />
            ) : (
              <Schedule
                trainings={trainings}
                loading={loadingSchedule}
                error={errorSchedule}
                onRefresh={(params) => loadSchedule(params)}
                onOpenTraining={(id) => setOpenTrainingId(id)}
              />
            )}
          </section>
        )}

        {/* ====== РЕЙТИНГ ====== */}
        {tab === "rating" && (
          <section className="screen">
            <div className="topbar">
              {openUserId ? (
                <button onClick={() => setOpenUserId(null)} style={linkBtnStyle}>
                  ← Назад
                </button>
              ) : (
                <h1 className="topbar-title">Рейтинг</h1>
              )}

              <button onClick={loadRating} style={linkBtnStyle}>
                Обновить
              </button>
            </div>

            {openUserId ? (
              <Profile userId={openUserId} />
            ) : loadingRating ? (
              <div className="empty">Загрузка...</div>
            ) : errorRating ? (
              <div className="empty">{errorRating}</div>
            ) : rating.length === 0 ? (
              <div className="empty">Рейтинг не загрузился или пуст</div>
            ) : (
              rating.map((p, idx) => (
                <div
                  className="card"
                  key={p.user_id ?? p.id ?? idx}
                  onClick={() => setOpenUserId(p.user_id)}
                  role="button"
                  tabIndex={0}
                  style={{ cursor: "pointer" }}
                  onKeyDown={(ev) => {
                    if ((ev.key === "Enter" || ev.key === " ") && p.user_id) setOpenUserId(p.user_id);
                  }}
                >
                  <div className="card-title">
                    {(p.place ?? idx + 1) + "."} {p.first_name || ""} {p.last_name || ""}{" "}
                    {p.username ? `(@${p.username})` : ""}
                  </div>
                  <div className="muted">
                    Очки: {p.rating ?? p.avg_score ?? "—"} • Кубки: {p.cups ?? "—"}
                  </div>
                  <div className="muted">Уровень: {p.level_name ?? p.level_title ?? "—"}</div>
                </div>
              ))
            )}
          </section>
        )}

        {/* ====== ПРОФИЛЬ ====== */}
        {tab === "profile" && (
          <section className="screen">
            <div className="topbar">
              <h1 className="topbar-title">Профиль</h1>
              <button onClick={() => window.location.reload()} style={linkBtnStyle}>
                Обновить
              </button>
            </div>
            <Profile />
          </section>
        )}

        {/* ====== УВЕДОМЛЕНИЯ ====== */}
        {tab === "notifications" && (
          <section className="screen">
            <div className="topbar">
              <h1 className="topbar-title">Уведомления</h1>
              <button onClick={loadNotifs} style={linkBtnStyle}>
                Обновить
              </button>
            </div>

            {loadingNotifs ? (
              <div className="empty">Загрузка...</div>
            ) : errorNotifs ? (
              <div className="empty">{errorNotifs}</div>
            ) : notifications.length === 0 ? (
              <div className="empty">У вас ещё нет уведомлений</div>
            ) : (
              notifications.map((n) => (
                <div className="card" key={n.id}>
                  <div className="card-title">{n.title ?? "Уведомление"}</div>
                  <div className="muted">{n.text ?? n.message ?? ""}</div>
                </div>
              ))
            )}
          </section>
        )}

        {/* ====== ЕЩЁ ====== */}
        {tab === "more" && (
          <section className="screen">
            <div className="topbar">
              <h1 className="topbar-title">Ещё</h1>
              <span />
            </div>

            <div className="card">
              <div className="card-title">Акции</div>
              <div className="muted">Статичная страница (дальше по ТЗ)</div>
            </div>

            <div className="card">
              <div className="card-title">Правила</div>
              <div className="muted">Статичная страница (дальше по ТЗ)</div>
            </div>

            <div className="card">
              <div className="card-title">Контакты</div>
              <div className="muted">Статичная страница (дальше по ТЗ)</div>
            </div>
          </section>
        )}
      </div>

      <nav className="tabbar">
        <button className={`tabbtn ${tab === "schedule" ? "active" : ""}`} onClick={() => safeSetTab("schedule")}>
          Главная
        </button>
        <button className={`tabbtn ${tab === "rating" ? "active" : ""}`} onClick={() => safeSetTab("rating")}>
          Рейтинг
        </button>
        <button className={`tabbtn ${tab === "profile" ? "active" : ""}`} onClick={() => safeSetTab("profile")}>
          Профиль
        </button>
        <button
          className={`tabbtn ${tab === "notifications" ? "active" : ""}`}
          onClick={() => safeSetTab("notifications")}
        >
          Уведомления
        </button>
        <button className={`tabbtn ${tab === "more" ? "active" : ""}`} onClick={() => safeSetTab("more")}>
          Ещё
        </button>
      </nav>
    </div>
  );
}
