import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiFetch, extractItems } from '../api';
import RefreshButton from '../components/RefreshButton';

function normalizeStr(v) {
  if (v === null || v === undefined) return '';
  return String(v).trim();
}

function formatDateRu(dateStr) {
  const s = normalizeStr(dateStr);
  if (!s) return '—';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString('ru-RU');
}

function formatDateTimeRu(dateStr) {
  const s = normalizeStr(dateStr);
  if (!s) return '—';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function pickName(profile) {
  const fn = normalizeStr(profile?.first_name ?? profile?.firstName ?? '');
  const ln = normalizeStr(profile?.last_name ?? profile?.lastName ?? '');
  const full = `${fn} ${ln}`.trim();
  return full || normalizeStr(profile?.username ?? profile?.tg_username ?? 'Пользователь');
}

function pickGender(profile) {
  const g = normalizeStr(profile?.gender ?? profile?.sex ?? profile?.pol ?? '');
  if (!g) return '—';
  const low = g.toLowerCase();
  if (low.startsWith('m') || low.includes('муж')) return 'Мужской';
  if (low.startsWith('f') || low.includes('жен')) return 'Женский';
  return g;
}

function normalizeLevelLabel(nameRaw) {
  const n = normalizeStr(nameRaw).toLowerCase().replace(/\s+/g, '');
  if (!n) return 'Новичок';
  if (n.includes('нович')) return 'Новичок';
  if (n.includes('средний-') || n.includes('средний−')) return 'Средний-';
  if (n === 'средний') return 'Средний';
  if (n.includes('средний+')) return 'Средний+';
  return 'Средний';
}

function normalizePhone(raw) {
  return normalizeStr(raw);
}

function resolveAvatarUrl(raw) {
  const value = normalizeStr(raw);
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;

  try {
    return new URL(value, window.location.origin).toString();
  } catch {
    return value;
  }
}

export default function Profile({ onBack }) {
  const [loading, setLoading] = useState(true);
  const [errorText, setErrorText] = useState('');

  const [profile, setProfile] = useState(null);
  const [levels, setLevels] = useState([]);
  const [ratingMe, setRatingMe] = useState(null);

  const [editOpen, setEditOpen] = useState(false);
  const [tgSaving, setTgSaving] = useState(false);
  const [avatarSaving, setAvatarSaving] = useState(false);

  const avatarInputRef = useRef(null);

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    gender: 'male',
    birth_date: '',
    show_telegram: true,
  });

  const loadProfileData = useCallback(async () => {
    setLoading(true);
    setErrorText('');

    try {
      const [pRes, lRes, rRes] = await Promise.all([
        apiFetch('/api/v1/profile/me'),
        apiFetch('/api/v1/levels'),
        apiFetch('/api/v1/ratings/me'),
      ]);

      const p = pRes?.item ?? pRes ?? null;
      const l = extractItems(lRes) || [];
      const r = rRes?.item ?? rRes ?? null;

      setProfile(p);
      setLevels(l);
      setRatingMe(r);

      setForm({
        first_name: normalizeStr(p?.first_name ?? p?.firstName ?? ''),
        last_name: normalizeStr(p?.last_name ?? p?.lastName ?? ''),
        phone: normalizeStr(p?.phone ?? ''),
        gender: normalizeStr(p?.gender ?? p?.sex ?? 'male') || 'male',
        birth_date: normalizeStr(p?.birth_date ?? p?.birthDate ?? ''),
        show_telegram: Boolean(
          p?.is_telegram_public ??
            p?.show_telegram ??
            p?.telegram_visible ??
            p?.telegram_public ??
            true,
        ),
      });

      const need =
        !normalizeStr(p?.phone) ||
        !normalizeStr(p?.birth_date ?? p?.birthDate) ||
        !normalizeStr(p?.gender ?? p?.sex);

      if (need) setEditOpen(true);
    } catch (err) {
      setErrorText(err?.message || 'Ошибка загрузки профиля');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfileData();
  }, [loadProfileData]);

  const name = useMemo(() => (profile ? pickName(profile) : ''), [profile]);

  const avatarUrl = useMemo(() => resolveAvatarUrl(profile?.avatar_url), [profile]);
  const avatarFallbackLetter = useMemo(() => (name ? name[0].toUpperCase() : 'U'), [name]);

  const levelName = useMemo(() => {
    if (!profile) return '—';
    const levelId = profile?.level_id ?? profile?.levelId ?? null;

    if (levelId !== null && levelId !== undefined && levels.length) {
      const found = levels.find((x) => Number(x?.id) === Number(levelId));
      const nm = normalizeStr(found?.name ?? found?.title ?? '');
      if (nm) return normalizeLevelLabel(nm);
    }

    const raw = profile?.level_name ?? profile?.levelName ?? profile?.level ?? '';
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

  const tgName = useMemo(() => {
    const u = normalizeStr(profile?.tg_username ?? profile?.username ?? '');
    return u ? `@${u.replace(/^@/, '')}` : '—';
  }, [profile]);

  const hasActiveBan = Boolean(profile?.has_active_ban ?? profile?.hasActiveBan);
  const activeBanReason = normalizeStr(profile?.active_ban_reason ?? profile?.activeBanReason) || 'Причина не указана';
  const activeBanUntil = normalizeStr(profile?.active_ban_until ?? profile?.activeBanUntil);

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function saveTelegramVisibility(nextValue) {
    const prev = Boolean(form.show_telegram);
    setField('show_telegram', nextValue);
    setErrorText('');
    setTgSaving(true);

    try {
      const res = await apiFetch('/api/v1/profile/me', {
        method: 'PATCH',
        body: {
          is_telegram_public: Boolean(nextValue),
        },
      });

      const p = res?.item ?? res ?? null;
      if (p) setProfile(p);
    } catch (err) {
      setField('show_telegram', prev);
      setErrorText(err?.message || 'Не удалось сохранить настройки Telegram');
    } finally {
      setTgSaving(false);
    }
  }

  async function saveProfile() {
    setErrorText('');

    try {
      const payload = {
        first_name: normalizeStr(form.first_name),
        last_name: normalizeStr(form.last_name),
        phone: normalizePhone(form.phone),
        gender: normalizeStr(form.gender),
        birth_date: normalizeStr(form.birth_date),
        is_telegram_public: Boolean(form.show_telegram),
      };

      Object.keys(payload).forEach((k) => {
        if (payload[k] === '' || payload[k] === null || payload[k] === undefined) {
          delete payload[k];
        }
      });

      const res = await apiFetch('/api/v1/profile/me', {
        method: 'PATCH',
        body: payload,
      });

      const p = res?.item ?? res ?? null;
      if (p) setProfile(p);
      setEditOpen(false);
    } catch (err) {
      setErrorText(err?.message || 'Ошибка сохранения профиля');
    }
  }

  async function uploadAvatar(file) {
    if (!file) return;
    if (!String(file.type || '').startsWith('image/')) {
      setErrorText('Для аватара можно выбрать только изображение.');
      return;
    }

    setErrorText('');
    setAvatarSaving(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await apiFetch('/api/v1/profile/me/avatar', {
        method: 'POST',
        body: formData,
      });
      const p = res?.item ?? res ?? null;
      if (p) setProfile(p);
    } catch (err) {
      setErrorText(err?.message || 'Не удалось загрузить аватар');
    } finally {
      setAvatarSaving(false);
      if (avatarInputRef.current) {
        avatarInputRef.current.value = '';
      }
    }
  }

  async function deleteAvatar() {
    setErrorText('');
    setAvatarSaving(true);
    try {
      const res = await apiFetch('/api/v1/profile/me/avatar', {
        method: 'DELETE',
      });
      const p = res?.item ?? res ?? null;
      if (p) setProfile(p);
    } catch (err) {
      setErrorText(err?.message || 'Не удалось удалить аватар');
    } finally {
      setAvatarSaving(false);
    }
  }

  const onPickAvatarClick = () => {
    avatarInputRef.current?.click();
  };

  return (
    <>
      <header className="topbar">
        <button type="button" className="back-btn" onClick={onBack} aria-label="Назад">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <h1 className="topbar-title">Мой профиль</h1>
        <RefreshButton onClick={loadProfileData} />
      </header>

      {loading ? <div className="loader">Загрузка…</div> : null}

      {!loading && errorText ? (
        <div className="empty-state" style={{ marginTop: 18 }}>
          <div className="empty-ico">⚠️</div>
          <h3>Ошибка</h3>
          <p>{errorText}</p>
        </div>
      ) : null}

      {!loading && profile ? (
        <>
          <section className="profile-card profile-card-lg">
            <div className="profile-top">
              <div className="profile-avatar-stack">
                <div className="avatar-lg">
                  {avatarUrl ? (
                    <img src={avatarUrl} alt="Аватар профиля" className="avatar-lg-image" />
                  ) : (
                    <div className="avatar-lg-fallback">{avatarFallbackLetter}</div>
                  )}
                </div>

                <input
                  ref={avatarInputRef}
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={(ev) => uploadAvatar(ev.target.files?.[0] || null)}
                />

                <button
                  type="button"
                  className="secondary-btn avatar-action-btn"
                  onClick={onPickAvatarClick}
                  disabled={avatarSaving}
                >
                  {avatarSaving ? 'Загрузка…' : (avatarUrl ? 'Изменить аватар' : 'Добавить аватар')}
                </button>

                {avatarUrl ? (
                  <button
                    type="button"
                    className="ghost-btn avatar-action-btn"
                    onClick={deleteAvatar}
                    disabled={avatarSaving}
                  >
                    Удалить аватар
                  </button>
                ) : null}
              </div>

              <div className="profile-main">
                <div className="profile-name">{name}</div>

                <div className="profile-sub" style={{ marginTop: 6 }}>
                  Уровень: <b>{levelName}</b>
                </div>

                {hasActiveBan ? (
                  <div className="ban-alert-card">
                    <div className="ban-alert-title">Активный бан</div>
                    <div className="ban-alert-text">Причина: {activeBanReason}</div>
                    <div className="ban-alert-text">До: {activeBanUntil ? formatDateTimeRu(activeBanUntil) : 'бессрочно'}</div>
                  </div>
                ) : null}

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
                      {normalizeStr(profile?.phone) || '—'}
                    </span>
                  </div>
                </div>

                <div className="settings-list" style={{ marginTop: 12 }}>
                  <div className="settings-item" style={{ cursor: 'default' }}>
                    <div className="settings-item-left">
                      <div className="settings-icon" style={{ background: 'rgba(47, 125, 246, 0.12)' }}>
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
                        disabled={tgSaving}
                        onChange={(ev) => saveTelegramVisibility(ev.target.checked)}
                      />
                      <span className="toggle-circle" />
                    </label>
                  </div>

                  <div className="modal-text" style={{ marginTop: 8, opacity: 0.75 }}>
                    Если выключить, другие игроки не смогут перейти к вам в Telegram из рейтинга.
                  </div>
                </div>
              </div>
            </div>
          </section>

          <button className="primary-btn" onClick={() => setEditOpen(true)}>
            Редактировать профиль
          </button>
        </>
      ) : null}

      {editOpen ? (
        <div className="modal-backdrop" onClick={() => setEditOpen(false)}>
          <div className="modal" onClick={(ev) => ev.stopPropagation()}>
            <div className="modal-title">Редактирование профиля</div>

            <div className="modal-text" style={{ marginTop: 8, opacity: 0.75 }}>
              Заполните профиль: пол, дата рождения и телефон нужны для записи на игры.
            </div>

            <div className="form-grid" style={{ marginTop: 12 }}>
              <div className="field">
                <div className="field-label">Имя</div>
                <input
                  className="input"
                  value={form.first_name}
                  onChange={(ev) => setField('first_name', ev.target.value)}
                  placeholder="Имя"
                />
              </div>

              <div className="field">
                <div className="field-label">Фамилия</div>
                <input
                  className="input"
                  value={form.last_name}
                  onChange={(ev) => setField('last_name', ev.target.value)}
                  placeholder="Фамилия"
                />
              </div>

              <div className="field">
                <div className="field-label">Телефон</div>
                <input
                  className="input"
                  value={form.phone}
                  onChange={(ev) => setField('phone', ev.target.value)}
                  placeholder="+7..."
                />
              </div>

              <div className="field">
                <div className="field-label">Пол</div>
                <select
                  className="select"
                  value={form.gender}
                  onChange={(ev) => setField('gender', ev.target.value)}
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
                  onChange={(ev) => setField('birth_date', ev.target.value)}
                />
              </div>
            </div>

            <div className="actions" style={{ marginTop: 14 }}>
              <button type="button" className="secondary-btn" onClick={() => setEditOpen(false)}>
                Отмена
              </button>

              <button type="button" className="primary-btn" onClick={saveProfile}>
                Сохранить
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
