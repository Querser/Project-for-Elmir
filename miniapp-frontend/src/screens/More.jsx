import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api';
import RefreshButton from '../components/RefreshButton';
import { resolveMediaUrl } from '../utils/media';

const DEFAULT_PUBLIC_TEXTS = {
  contacts_text: 'Контакты пока не заполнены.',
  rules_text: 'Правила пока не заполнены.',
  promotions_text: 'Акции пока не заполнены.',
};

function formatName(profile) {
  const first = (profile?.first_name ?? profile?.firstName ?? '').toString().trim();
  const last = (profile?.last_name ?? profile?.lastName ?? '').toString().trim();
  const username = (profile?.username ?? '').toString().trim();
  const full = `${first} ${last}`.trim();
  return full || (username ? `@${username}` : 'Пользователь');
}

function normalizeText(value) {
  if (value == null) return '';
  return String(value).trim();
}

function openExternal(url) {
  const href = normalizeText(url);
  if (!href) return;

  try {
    const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : null;
    if (tg?.openLink) {
      tg.openLink(href);
      return;
    }
  } catch {
    // ignore
  }

  try {
    window.open(href, '_blank', 'noopener,noreferrer');
  } catch {
    // ignore
  }
}

function RichText({ text }) {
  const value = normalizeText(text);
  if (!value) return null;

  const URL_RE = /(https?:\/\/[^\s]+)/gi;
  const lines = value.split(/\r?\n/);

  return (
    <div className="richtext-content">
      {lines.map((line, lineIndex) => {
        const parts = line.split(URL_RE);
        return (
          <p key={`${line}-${lineIndex}`} className="richtext-line">
            {parts.map((part, partIndex) => {
              const trimmed = normalizeText(part);
              const isLink = /^https?:\/\//i.test(trimmed);
              if (isLink) {
                return (
                  <a
                    key={`${part}-${partIndex}`}
                    href={trimmed}
                    className="richtext-link"
                    onClick={(ev) => {
                      ev.preventDefault();
                      openExternal(trimmed);
                    }}
                  >
                    {trimmed}
                  </a>
                );
              }
              return <span key={`${part}-${partIndex}`}>{part}</span>;
            })}
          </p>
        );
      })}
    </div>
  );
}

export default function More({ darkMode, onToggleDarkMode, onOpenProfile }) {
  const [profile, setProfile] = useState(null);
  const [rating, setRating] = useState(null);
  const [publicTexts, setPublicTexts] = useState(DEFAULT_PUBLIC_TEXTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(null); // 'promotions' | 'rules' | 'contacts'
  const [avatarFailed, setAvatarFailed] = useState(false);

  const isThemeControlled = typeof darkMode === 'boolean' && typeof onToggleDarkMode === 'function';
  const [darkLocal, setDarkLocal] = useState(() => localStorage.getItem('theme') === 'dark');
  const dark = isThemeControlled ? darkMode : darkLocal;

  useEffect(() => {
    document.body.classList.toggle('theme-dark', Boolean(dark));
    if (!isThemeControlled) {
      localStorage.setItem('theme', dark ? 'dark' : 'light');
    }
  }, [dark, isThemeControlled]);

  const load = async () => {
    try {
      setLoading(true);
      setError('');

      const [profileRes, ratingRes, settingsRes] = await Promise.all([
        apiFetch('/api/v1/profile/me'),
        apiFetch('/api/v1/ratings/me'),
        apiFetch('/api/v1/settings/public'),
      ]);

      setProfile(profileRes || null);
      setRating(ratingRes || null);
      setPublicTexts({
        contacts_text: normalizeText(settingsRes?.contacts_text) || DEFAULT_PUBLIC_TEXTS.contacts_text,
        rules_text: normalizeText(settingsRes?.rules_text) || DEFAULT_PUBLIC_TEXTS.rules_text,
        promotions_text: normalizeText(settingsRes?.promotions_text) || DEFAULT_PUBLIC_TEXTS.promotions_text,
      });
    } catch (err) {
      setError(err?.message || 'Не удалось загрузить данные аккаунта');
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
    if (!rating) return 'Добро пожаловать в MosVolley';
    const cups = rating?.cups ?? 0;
    const pos = rating?.position ?? rating?.place ?? '—';
    const total = rating?.total_users ?? rating?.total ?? '—';
    return `Кубки: ${cups} · Место: ${pos}/${total}`;
  }, [rating]);

  const avatarUrl = useMemo(() => resolveMediaUrl(profile?.avatar_url), [profile]);

  useEffect(() => {
    setAvatarFailed(false);
  }, [avatarUrl]);

  const toggleTheme = (checked) => {
    if (isThemeControlled) {
      onToggleDarkMode?.(checked);
      return;
    }
    setDarkLocal(Boolean(checked));
  };

  const pageTitle = useMemo(() => {
    if (page === 'promotions') return 'Акции';
    if (page === 'rules') return 'Правила';
    if (page === 'contacts') return 'Контакты';
    return '';
  }, [page]);

  const pageText = useMemo(() => {
    if (page === 'promotions') return publicTexts.promotions_text;
    if (page === 'rules') return publicTexts.rules_text;
    if (page === 'contacts') return publicTexts.contacts_text;
    return '';
  }, [page, publicTexts]);

  return (
    <>
      <header className="topbar">
        <h1 className="topbar-title">Ещё</h1>
        <RefreshButton onClick={load} />
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
              <div className="profile-avatar">
                {avatarUrl && !avatarFailed ? (
                  <img
                    src={avatarUrl}
                    alt={name || 'Аватар'}
                    className="profile-avatar-image"
                    onError={() => setAvatarFailed(true)}
                    loading="lazy"
                  />
                ) : (name?.slice(0, 1)?.toUpperCase() || 'U')}
              </div>
              <div>
                <h2 className="profile-name">{name}</h2>
                <p className="profile-sub">{subtitle}</p>
              </div>
            </div>

            <div className="settings-list" style={{ marginTop: 12 }}>
              <div className="settings-item" role="button" tabIndex={0} onClick={() => setPage('promotions')}>
                <div className="settings-item-left">
                  <div className="settings-icon">🔥</div>
                  <div>
                    <div className="settings-label">Акции</div>
                    <div className="settings-value">Актуальные предложения</div>
                  </div>
                </div>
                <div className="settings-chevron">›</div>
              </div>

              <div className="settings-item" role="button" tabIndex={0} onClick={() => setPage('rules')}>
                <div className="settings-item-left">
                  <div className="settings-icon">📄</div>
                  <div>
                    <div className="settings-label">Правила</div>
                    <div className="settings-value">Порядок записи и посещений</div>
                  </div>
                </div>
                <div className="settings-chevron">›</div>
              </div>

              <div className="settings-item" role="button" tabIndex={0} onClick={() => setPage('contacts')}>
                <div className="settings-item-left">
                  <div className="settings-icon">☎️</div>
                  <div>
                    <div className="settings-label">Контакты</div>
                    <div className="settings-value">Связь с администрацией</div>
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
            </div>
          </>
        ) : null}
      </div>

      {page ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <div className="modal-title">{pageTitle}</div>
            <div className="modal-body">
              <RichText text={pageText} />
            </div>
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
