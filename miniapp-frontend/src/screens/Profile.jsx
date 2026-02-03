import React, { useEffect, useMemo, useState } from "react";
import { apiFetch, extractItems } from "../api";

function normalizeStr(v) {
  if (v === null || v === undefined) return "";
  return String(v).trim();
}

function formatDateRu(dateStr) {
  const s = normalizeStr(dateStr);
  if (!s) return "—";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString("ru-RU");
}

function pickName(profile) {
  const fn = normalizeStr(profile?.first_name ?? profile?.firstName ?? "");
  const ln = normalizeStr(profile?.last_name ?? profile?.lastName ?? "");
  const full = `${fn} ${ln}`.trim();
  return (
    full ||
    normalizeStr(profile?.username ?? profile?.tg_username ?? "Пользователь")
  );
}

function pickGender(profile) {
  const g = normalizeStr(profile?.gender ?? profile?.sex ?? profile?.pol ?? "");
  if (!g) return "—";
  const low = g.toLowerCase();
  if (low.startsWith("m") || low.includes("муж")) return "Мужской";
  if (low.startsWith("f") || low.includes("жен")) return "Женский";
  return g;
}

function normalizeLevelLabel(nameRaw) {
  const n = normalizeStr(nameRaw).toLowerCase().replace(/\s+/g, "");
  if (!n) return "—";
  if (n.includes("нович")) return "Новичок";
  if (n.includes("средний-") || n.includes("средний−")) return "Средний-";
  if (n === "средний") return "Средний";
  if (n.includes("средний+")) return "Средний+";
  return "Средний";
}

function normalizePhone(raw) {
  return normalizeStr(raw);
}

export default function Profile({ onBack }) {
  const [loading, setLoading] = useState(true);
  const [errorText, setErrorText] = useState("");

  const [profile, setProfile] = useState(null);
  const [levels, setLevels] = useState([]);
  const [ratingMe, setRatingMe] = useState(null);

  const [editOpen, setEditOpen] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    gender: "male",
    birth_date: "",
    show_telegram: true, // UI-имя, на бэк уходит как is_telegram_public
  });

  useEffect(() => {
    let alive = true;

    async function load() {
      setLoading(true);
      setErrorText("");

      try {
        const [pRes, lRes, rRes] = await Promise.all([
          apiFetch("/api/v1/profile/me"),
          apiFetch("/api/v1/levels"),
          apiFetch("/api/v1/ratings/me"),
        ]);

        const p = pRes?.item ?? pRes ?? null;
        const l = extractItems(lRes) || [];
        const r = rRes?.item ?? rRes ?? null;

        if (!alive) return;

        setProfile(p);
        setLevels(l);
        setRatingMe(r);

        setForm({
          first_name: normalizeStr(p?.first_name ?? p?.firstName ?? ""),
          last_name: normalizeStr(p?.last_name ?? p?.lastName ?? ""),
          phone: normalizeStr(p?.phone ?? ""),
          gender: normalizeStr(p?.gender ?? p?.sex ?? "male") || "male",
          birth_date: normalizeStr(p?.birth_date ?? p?.birthDate ?? ""),
          // ВАЖНО: читаем именно is_telegram_public (как на бэке),
          // но оставляем в UI-форме show_telegram.
          show_telegram: Boolean(
            p?.is_telegram_public ??
              p?.show_telegram ??
              p?.telegram_visible ??
              p?.telegram_public ??
              true
          ),
        });

        // если профиль не заполнен — открываем редактирование
        const need =
          !normalizeStr(p?.phone) ||
          !normalizeStr(p?.birth_date ?? p?.birthDate) ||
          !normalizeStr(p?.gender ?? p?.sex);

        if (need) setEditOpen(true);
      } catch (err) {
        if (!alive) return;
        setErrorText(err?.message || "Ошибка загрузки профиля");
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();

    return () => {
      alive = false;
    };
  }, []);

  const name = useMemo(() => (profile ? pickName(profile) : ""), [profile]);

  const levelName = useMemo(() => {
    if (!profile) return "—";
    const levelId = profile?.level_id ?? profile?.levelId ?? null;

    if (levelId !== null && levelId !== undefined && levels.length) {
      const found = levels.find((x) => Number(x?.id) === Number(levelId));
      const nm = normalizeStr(found?.name ?? found?.title ?? "");
      if (nm) return normalizeLevelLabel(nm);
    }

    const raw = profile?.level_name ?? profile?.levelName ?? profile?.level ?? "";
    return normalizeLevelLabel(raw);
  }, [profile, levels]);

  const ratingPoints = useMemo(() => {
    if (!ratingMe) return 0;
    return (
      ratingMe?.points ??
      ratingMe?.score ??
      ratingMe?.rating_points ??
      ratingMe?.rating ??
      0
    );
  }, [ratingMe]);

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function saveProfile() {
    setErrorText("");

    try {
      // КЛЮЧЕВОЙ ФИКС 422:
      // - не шлём пустую строку в birth_date (date-поле)
      // - не шлём лишнее show_telegram (на бэке is_telegram_public)
      const payload = {
        first_name: normalizeStr(form.first_name),
        last_name: normalizeStr(form.last_name),
        phone: normalizePhone(form.phone),
        gender: normalizeStr(form.gender),
        birth_date: normalizeStr(form.birth_date),
        is_telegram_public: Boolean(form.show_telegram),
      };

      // убираем пустые строки, чтобы FastAPI/Pydantic не ловил date=""
      Object.keys(payload).forEach((k) => {
        if (payload[k] === "" || payload[k] === null || payload[k] === undefined) {
          delete payload[k];
        }
      });

      const updated = await apiFetch("/api/v1/profile/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const p = updated?.item ?? updated ?? null;
      setProfile(p);
      setEditOpen(false);
    } catch (err) {
      setErrorText(err?.message || "Ошибка сохранения профиля");
    }
  }

  const tgName = useMemo(() => {
    const u = normalizeStr(profile?.username ?? "");
    const t = normalizeStr(profile?.tg_username ?? "");
    const best = u || t;
    return best ? `@${best.replace(/^@/, "")}` : "—";
  }, [profile]);

  return (
    <div className="screen active">
      <div className="topbar">
        <button className="back-btn" onClick={() => (onBack ? onBack() : null)}>
          <svg viewBox="0 0 24 24">
            <path
              d="M15 18l-6-6 6-6"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
        <h1 className="topbar-title" style={{ fontSize: 22 }}>
          Профиль
        </h1>
        <div style={{ width: 40 }} />
      </div>

      {loading ? <div className="loader">Загрузка…</div> : null}

      {!loading && errorText ? (
        <div className="empty-state">
          <span className="empty-ico">⚠️</span>
          Ошибка
          <div style={{ marginTop: 6 }}>{errorText}</div>
        </div>
      ) : null}

      {!loading && !errorText && profile ? (
        <>
          <div className="profile-card" style={{ cursor: "default" }}>
            <div className="profile-avatar">{name?.[0]?.toUpperCase() || "•"}</div>

            <div className="profile-main">
              <div className="profile-name">{name}</div>

              <div className="profile-sub" style={{ marginTop: 6 }}>
                Уровень: <b>{levelName}</b>
              </div>

              <div className="details-card" style={{ marginTop: 12 }}>
                <div className="label-row">
                  <span className="label-muted">Рейтинг игрока</span>
                  <span className="label-strong">{ratingPoints} очков</span>
                </div>
                <div className="label-row">
                  <span className="label-muted">Пол</span>
                  <span className="label-strong">{pickGender(profile)}</span>
                </div>
                <div className="label-row">
                  <span className="label-muted">Дата рождения</span>
                  <span className="label-strong">
                    {formatDateRu(profile?.birth_date ?? profile?.birthDate)}
                  </span>
                </div>
                <div className="label-row" style={{ marginBottom: 0 }}>
                  <span className="label-muted">Телефон</span>
                  <span className="label-strong">
                    {normalizeStr(profile?.phone) || "—"}
                  </span>
                </div>
              </div>

              <div className="settings-list" style={{ marginTop: 12 }}>
                <div className="settings-item" style={{ cursor: "default" }}>
                  <div className="settings-item-left">
                    <div
                      className="settings-icon"
                      style={{ background: "rgba(47, 125, 246, 0.12)" }}
                    >
                      ✈️
                    </div>
                    <div>
                      <div className="settings-label">Telegram</div>
                      <div className="settings-value">{tgName}</div>
                    </div>
                  </div>

                  <label className="toggle" title="Разрешить переход по Telegram">
                    <input
                      type="checkbox"
                      checked={Boolean(form.show_telegram)}
                      onChange={(ev) => setField("show_telegram", ev.target.checked)}
                    />
                    <span className="toggle-circle" />
                  </label>
                </div>

                <div className="modal-text" style={{ marginTop: 8, opacity: 0.75 }}>
                  Если выключить — другие игроки не смогут перейти к тебе в Telegram из рейтинга.
                </div>
              </div>
            </div>
          </div>

          <button className="primary-btn" onClick={() => setEditOpen(true)}>
            Редактировать профиль
          </button>

          <button
            className="ghost-btn"
            onClick={async () => {
              try {
                await apiFetch("/api/v1/profile/me", {
                  method: "PATCH",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    is_telegram_public: Boolean(form.show_telegram),
                  }),
                });
              } catch {
                // ignore
              }
            }}
            style={{ marginTop: 10 }}
          >
            Сохранить настройки Telegram
          </button>
        </>
      ) : null}

      {editOpen ? (
        <div className="modal-backdrop" onClick={() => setEditOpen(false)}>
          <div className="modal" onClick={(ev) => ev.stopPropagation()}>
            <div className="modal-title">Редактирование профиля</div>

            <div className="modal-text" style={{ marginTop: 8, opacity: 0.75 }}>
              Заполни профиль: пол, дата рождения и телефон нужны для записи на игры.
            </div>

            <div className="form-grid" style={{ marginTop: 12 }}>
              <div className="field">
                <div className="field-label">Имя</div>
                <input
                  className="input"
                  value={form.first_name}
                  onChange={(ev) => setField("first_name", ev.target.value)}
                  placeholder="Имя"
                />
              </div>

              <div className="field">
                <div className="field-label">Фамилия</div>
                <input
                  className="input"
                  value={form.last_name}
                  onChange={(ev) => setField("last_name", ev.target.value)}
                  placeholder="Фамилия"
                />
              </div>

              <div className="field">
                <div className="field-label">Телефон</div>
                <input
                  className="input"
                  value={form.phone}
                  onChange={(ev) => setField("phone", ev.target.value)}
                  placeholder="+7..."
                />
              </div>

              <div className="field">
                <div className="field-label">Пол</div>
                <select
                  className="select"
                  value={form.gender}
                  onChange={(ev) => setField("gender", ev.target.value)}
                >
                  <option value="male">Мужской</option>
                  <option value="female">Женский</option>
                </select>
              </div>

              <div className="field">
                <div className="field-label">Дата рождения</div>
                <input
                  className="input"
                  type="date"
                  value={form.birth_date}
                  onChange={(ev) => setField("birth_date", ev.target.value)}
                />
              </div>

              <div className="field" style={{ gridColumn: "1 / -1" }}>
                <div className="field-label">Разрешить переход по Telegram</div>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(form.show_telegram)}
                    onChange={(ev) => setField("show_telegram", ev.target.checked)}
                  />
                  <span className="toggle-circle" />
                </label>
              </div>
            </div>

            {errorText ? (
              <div className="modal-text" style={{ color: "var(--danger)" }}>
                {errorText}
              </div>
            ) : null}

            <div className="modal-actions">
              <button className="primary-btn" onClick={saveProfile}>
                Сохранить
              </button>
              <button className="ghost-btn" onClick={() => setEditOpen(false)}>
                Отмена
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}