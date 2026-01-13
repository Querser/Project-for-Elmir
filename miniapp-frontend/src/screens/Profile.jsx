// src/screens/Profile.jsx
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch } from "../api";
import DevAuth from "../components/DevAuth";
import { getTelegramInitData } from "../auth";

function toISODateInput(d) {
  if (!d) return "";
  if (typeof d === "string" && /^\d{4}-\d{2}-\d{2}$/.test(d)) return d;
  try {
    const dt = new Date(d);
    const y = dt.getFullYear();
    const m = String(dt.getMonth() + 1).padStart(2, "0");
    const day = String(dt.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  } catch {
    return "";
  }
}

function pickMeEndpoints() {
  return ["/api/v1/users/me", "/api/v1/profile", "/api/v1/me"];
}

function pickUserEndpoint(userId) {
  return [`/api/v1/users/${userId}`, `/api/v1/profile/${userId}`];
}

function unwrap(res) {
  if (!res) return res;
  if (res.ok === true && res.result != null) return res.result;
  return res;
}

/**
 * Компонент без собственного topbar — чтобы внешний вид оставался как в исходном App.jsx.
 */
export default function Profile({ userId }) {
  const isMe = !userId;

  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(null);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const tgInfo = useMemo(() => getTelegramInitData(), []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      let res = null;

      if (isMe) {
        for (const ep of pickMeEndpoints()) {
          try {
            res = await apiGet(ep);
            break;
          } catch {
            // пробуем следующий endpoint
          }
        }
      } else {
        for (const ep of pickUserEndpoint(userId)) {
          try {
            res = await apiGet(ep);
            break;
          } catch {
            // пробуем следующий endpoint
          }
        }
      }

      const p = unwrap(res);
      if (!p) throw new Error("Профиль не найден (проверь /users/me или /profile).");

      setProfile(p);

      if (isMe) {
        setForm({
          first_name: p.first_name || "",
          last_name: p.last_name || "",
          phone: p.phone || "",
          gender: p.gender || "",
          birth_date: toISODateInput(p.birth_date),
          is_telegram_public: p.is_telegram_public ?? true,
        });
      } else {
        setForm(null);
      }
    } catch (e) {
      console.error(e);
      setProfile(null);
      setForm(null);
      setError(e?.message || "Не удалось загрузить профиль.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function save() {
    if (!form) return;
    setSaving(true);
    setError("");
    try {
      const payload = {
        first_name: form.first_name,
        last_name: form.last_name,
        phone: form.phone || null,
        gender: form.gender || null,
        birth_date: form.birth_date || null,
        is_telegram_public: !!form.is_telegram_public,
      };

      let ok = false;
      for (const ep of pickMeEndpoints()) {
        try {
          const res = await apiPatch(ep, payload);
          const p = unwrap(res);
          if (p) setProfile(p);
          ok = true;
          break;
        } catch {
          // пробуем следующий endpoint
        }
      }
      if (!ok) throw new Error("Не удалось сохранить (проверь PATCH /users/me или /profile).");

      await load();
    } catch (e) {
      console.error(e);
      const msg = e?.data?.detail || e?.data?.error?.message || e?.message || "Ошибка сохранения";
      setError(String(msg));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="empty">Загрузка...</div>;
  if (error && !profile) return <div className="empty">{error}</div>;
  if (!profile) return <div className="empty">Профиль недоступен</div>;

  return (
    <>
      {!tgInfo.initData && isMe ? <DevAuth onSaved={load} /> : null}

      <div className="card">
        <div className="card-title">
          {profile.first_name || ""} {profile.last_name || ""}
          {profile.username ? ` (@${profile.username})` : ""}
        </div>
        <div className="muted">Telegram ID: {profile.telegram_id ?? "—"}</div>
        <div className="muted">
          Рейтинг: {profile.rating ?? "—"} • Кубки: {profile.cups ?? "—"}
        </div>
        <div className="muted">Уровень: {profile.level_name ?? profile.level_id ?? "—"}</div>
      </div>

      {isMe && form ? (
        <div className="card">
          <div className="card-title">Редактирование</div>

          <label style={{ display: "block", marginTop: 10 }}>
            <div className="muted" style={{ marginBottom: 6 }}>Имя</div>
            <input
              style={{ width: "100%", padding: 10, borderRadius: 12, border: "1px solid rgba(0,0,0,0.12)" }}
              value={form.first_name}
              onChange={(ev) => setForm({ ...form, first_name: ev.target.value })}
            />
          </label>

          <label style={{ display: "block", marginTop: 10 }}>
            <div className="muted" style={{ marginBottom: 6 }}>Фамилия</div>
            <input
              style={{ width: "100%", padding: 10, borderRadius: 12, border: "1px solid rgba(0,0,0,0.12)" }}
              value={form.last_name}
              onChange={(ev) => setForm({ ...form, last_name: ev.target.value })}
            />
          </label>

          <label style={{ display: "block", marginTop: 10 }}>
            <div className="muted" style={{ marginBottom: 6 }}>Телефон</div>
            <input
              style={{ width: "100%", padding: 10, borderRadius: 12, border: "1px solid rgba(0,0,0,0.12)" }}
              value={form.phone}
              onChange={(ev) => setForm({ ...form, phone: ev.target.value })}
              placeholder="+7..."
            />
          </label>

          <label style={{ display: "block", marginTop: 10 }}>
            <div className="muted" style={{ marginBottom: 6 }}>Пол</div>
            <select
              style={{ width: "100%", padding: 10, borderRadius: 12, border: "1px solid rgba(0,0,0,0.12)" }}
              value={form.gender}
              onChange={(ev) => setForm({ ...form, gender: ev.target.value })}
            >
              <option value="">—</option>
              <option value="male">Мужской</option>
              <option value="female">Женский</option>
            </select>
          </label>

          <label style={{ display: "block", marginTop: 10 }}>
            <div className="muted" style={{ marginBottom: 6 }}>Дата рождения</div>
            <input
              type="date"
              style={{ width: "100%", padding: 10, borderRadius: 12, border: "1px solid rgba(0,0,0,0.12)" }}
              value={form.birth_date}
              onChange={(ev) => setForm({ ...form, birth_date: ev.target.value })}
            />
          </label>

          <label style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 12 }}>
            <input
              type="checkbox"
              checked={!!form.is_telegram_public}
              onChange={(ev) => setForm({ ...form, is_telegram_public: ev.target.checked })}
            />
            <span className="muted">Показывать Telegram в профиле</span>
          </label>

          <button
            onClick={save}
            disabled={saving}
            style={{
              marginTop: 12,
              width: "100%",
              padding: "10px 12px",
              borderRadius: 14,
              border: "none",
              background: "#2f7df6",
              color: "#fff",
              fontWeight: 700,
              cursor: "pointer",
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? "Сохранение..." : "Сохранить"}
          </button>

          {error ? (
            <div className="muted" style={{ color: "#ef4444", fontWeight: 600, marginTop: 10 }}>
              {error}
            </div>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
