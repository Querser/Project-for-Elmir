import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api";
import { clearAuth } from "../auth";

function formatName(p) {
  const first = (p?.first_name ?? p?.firstName ?? "").toString().trim();
  const last = (p?.last_name ?? p?.lastName ?? "").toString().trim();
  const username = (p?.username ?? "").toString().trim();
  const full = `${first} ${last}`.trim();
  return full || (username ? `@${username}` : "Пользователь");
}

export default function More({ darkMode, onToggleDarkMode, onOpenProfile, onLogout }) {
  const [profile, setProfile] = useState(null);
  const [rating, setRating] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(null); // 'promotions' | 'rules' | 'contacts'

  // тема: controlled (через пропсы) или uncontrolled (localStorage)
  const isThemeControlled = typeof darkMode === "boolean" && typeof onToggleDarkMode === "function";
  const [darkLocal, setDarkLocal] = useState(() => localStorage.getItem("theme") === "dark");
  const dark = isThemeControlled ? darkMode : darkLocal;

  useEffect(() => {
    document.body.classList.toggle("theme-dark", Boolean(dark));
    if (!isThemeControlled) {
      localStorage.setItem("theme", dark ? "dark" : "light");
    }
  }, [dark, isThemeControlled]);

  const load = async () => {
    try {
      setLoading(true);
      setError("");

      const [p, r] = await Promise.all([
        apiFetch("/api/v1/profile/me"),
        apiFetch("/api/v1/ratings/me"),
      ]);

      setProfile(p || null);
      setRating(r || null);
    } catch (err) {
      setError(err?.message || "Не удалось загрузить данные аккаунта");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (cancelled) return;
      await load();
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const name = useMemo(() => formatName(profile), [profile]);
  const subtitle = useMemo(() => {
    if (!rating) return "Добро пожаловать в UfaVolley";
    const cups = rating?.cups ?? 0;
    const pos = rating?.position ?? rating?.place ?? "—";
    const total = rating?.total_users ?? rating?.total ?? "—";
    return `Кубки: ${cups} · Место: ${pos}/${total}`;
  }, [rating]);

  const handleLogout = () => {
    if (typeof onLogout === "function") {
      onLogout();
      return;
    }
    clearAuth();
    window.location.reload();
  };

  const toggleTheme = (checked) => {
    if (isThemeControlled) {
      onToggleDarkMode?.(checked);
      return;
    }
    setDarkLocal(Boolean(checked));
  };

  const pageTitle = useMemo(() => {
    if (page === "promotions") return "Акции";
    if (page === "rules") return "Правила";
    if (page === "contacts") return "Контакты";
    return "";
  }, [page]);

  const pageBody = useMemo(() => {
    if (page === "promotions") {
      return (
        <>
          <p>
            Здесь публикуются актуальные акции и специальные предложения. Раздел сделан как статическая страница
            (по плану этапа 12). Контент будет обновляться администратором.
          </p>
          <ul style={{ marginTop: 10, paddingLeft: 18 }}>
            <li>Скидка на первое посещение (если включена администратором)</li>
            <li>Бонусы за регулярное посещение</li>
            <li>Акции на абонементы</li>
          </ul>
        </>
      );
    }

    if (page === "rules") {
      return (
        <>
          <p>Ключевые правила посещения и записи. Точный текст правил может быть уточнён администратором.</p>
          <ul style={{ marginTop: 10, paddingLeft: 18 }}>
            <li>Запись на тренировку открывается заранее и закрывается по расписанию.</li>
            <li>Отмена записи доступна не позднее, чем за 2 часа до начала (по ТЗ).</li>
            <li>Опоздания и неявки могут влиять на рейтинг/доступ к тренировкам (по правилам клуба).</li>
            <li>Соблюдайте технику безопасности и уважайте участников.</li>
          </ul>
        </>
      );
    }

    if (page === "contacts") {
      return (
        <>
          <p>Контакты администратора. В текущей версии (этап 12) раздел реализован как статическое окно.</p>
          <div className="card" style={{ marginTop: 10 }}>
            <div className="label-row">
              <span className="label-muted">Телефон</span>
              <span className="label-strong">Уточняется</span>
            </div>
            <div className="label-row">
              <span className="label-muted">Telegram</span>
              <span className="label-strong">Уточняется</span>
            </div>
            <p className="details-note" style={{ marginTop: 10 }}>
              Если потребуется — добавим подгрузку контактов из backend/админки отдельным этапом.
            </p>
          </div>
        </>
      );
    }

    return null;
  }, [page]);

  return (
    <>
      <header className="topbar">
        <h1 className="topbar-title">Ещё</h1>
        <button className="icon-btn" type="button" onClick={load} aria-label="Обновить">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M4 4v6h6M20 20v-6h-6" />
            <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M20 8a8 8 0 00-14.8-3M4 16a8 8 0 0014.8 3" />
          </svg>
        </button>
      </header>

      <div className="content">
        {loading ? <div className="loader">Загрузка…</div> : null}

        {!loading && error ? (
          <div className="empty-state" style={{ marginTop: 18 }}>
            <div className="empty-ico">⚠️</div>
            <h3>Ошибка</h3>
            <p>{error}</p>
          </div>
        ) : null}

        {!loading && !error ? (
          <>
            <div className="profile-card" role="button" tabIndex={0} onClick={() => onOpenProfile?.()}>
              <div className="profile-avatar">{name?.slice(0, 1)?.toUpperCase() || "U"}</div>
              <div>
                <h2 className="profile-name">{name}</h2>
                <p className="profile-sub">{subtitle}</p>
              </div>
            </div>

            <div className="settings-list" style={{ marginTop: 12 }}>
              <div className="settings-item" role="button" tabIndex={0} onClick={() => setPage("promotions")}>
                <div className="settings-item-left">
                  <div className="settings-icon">🔥</div>
                  <div>
                    <div className="settings-label">Акции</div>
                    <div className="settings-value">Специальные предложения</div>
                  </div>
                </div>
                <div className="settings-chevron">›</div>
              </div>

              <div className="settings-item" role="button" tabIndex={0} onClick={() => setPage("rules")}>
                <div className="settings-item-left">
                  <div className="settings-icon">📄</div>
                  <div>
                    <div className="settings-label">Правила</div>
                    <div className="settings-value">Как работает запись и отмена</div>
                  </div>
                </div>
                <div className="settings-chevron">›</div>
              </div>

              <div className="settings-item" role="button" tabIndex={0} onClick={() => setPage("contacts")}>
                <div className="settings-item-left">
                  <div className="settings-icon">☎️</div>
                  <div>
                    <div className="settings-label">Контакты</div>
                    <div className="settings-value">Связаться с администратором</div>
                  </div>
                </div>
                <div className="settings-chevron">›</div>
              </div>

              <div className="settings-item">
                <div className="settings-item-left">
                  <div className="settings-icon">🌓</div>
                  <div>
                    <div className="settings-label">Тёмная тема</div>
                    <div className="settings-value">Переключатель оформления</div>
                  </div>
                </div>

                <label className="toggle" aria-label="Тёмная тема">
                  <input
                    type="checkbox"
                    checked={Boolean(dark)}
                    onChange={(e) => toggleTheme(e.target.checked)}
                  />
                  <span className="toggle-circle" />
                </label>
              </div>

              <div className="settings-item" role="button" tabIndex={0} onClick={handleLogout}>
                <div className="settings-item-left">
                  <div
                    className="settings-icon"
                    style={{ background: "rgba(239,68,68,.1)", color: "var(--danger)" }}
                  >
                    ⎋
                  </div>
                  <div>
                    <div className="settings-label" style={{ color: "var(--danger)" }}>
                      Выйти
                    </div>
                    <div className="settings-value">Сбросить авторизацию</div>
                  </div>
                </div>
                <div className="settings-chevron">›</div>
              </div>
            </div>
          </>
        ) : null}
      </div>

      {page ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <div className="modal-title">{pageTitle}</div>
            <div className="modal-body">{pageBody}</div>
            <div className="modal-actions">
              <button className="primary-btn" type="button" onClick={() => setPage(null)}>
                Закрыть
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
