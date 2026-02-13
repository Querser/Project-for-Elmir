import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api';
import RefreshButton from '../components/RefreshButton';

function normalizeItems(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.results)) return data.results;
  return [];
}

function parseDate(value) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatWhen(dt) {
  if (!dt) return '';
  return dt.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function normalizeText(value) {
  if (value == null) return '';
  return String(value).trim();
}

function unique(list) {
  return Array.from(new Set(list.filter(Boolean)));
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
  } catch (e) {
    void e;
  }

  try {
    window.open(href, '_blank', 'noopener,noreferrer');
  } catch (e) {
    void e;
  }
}

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(null);
  const [expandedIds, setExpandedIds] = useState([]);

  const LIMIT = 50;

  const load = useCallback(async (opts = {}) => {
    const { offset = 0, append = false } = opts;
    try {
      setLoading(true);
      setError('');
      const data = await apiFetch(`/api/v1/notifications?offset=${offset}&limit=${LIMIT}`);
      const next = normalizeItems(data);
      setTotal(typeof data?.total === 'number' ? data.total : null);
      setItems((prev) => (append ? [...prev, ...next] : next));
      if (!append) {
        setExpandedIds([]);
      }
    } catch (err) {
      setError(err?.message || 'Не удалось загрузить уведомления');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load({ offset: 0, append: false });
  }, [load]);

  const sorted = useMemo(() => {
    const arr = [...items];
    arr.sort((a, b) => {
      const da = parseDate(a?.created_at ?? a?.createdAt)?.getTime() ?? 0;
      const db = parseDate(b?.created_at ?? b?.createdAt)?.getTime() ?? 0;
      return db - da;
    });
    return arr;
  }, [items]);

  const markRead = useCallback(async (id) => {
    if (!id) return;
    try {
      await apiFetch(`/api/v1/notifications/${id}/read`, { method: 'POST' });
      setItems((prev) =>
        prev.map((x) => {
          if ((x?.id ?? null) !== id) return x;
          return { ...x, is_read: true, isRead: true };
        }),
      );
    } catch (err) {
      void err;
    }
  }, []);

  const canLoadMore = useMemo(() => {
    if (loading) return false;
    if (total == null) return false;
    return items.length < total;
  }, [items.length, total, loading]);

  const loadMore = async () => {
    if (!canLoadMore) return;
    await load({ offset: items.length, append: true });
  };

  const toggleExpanded = (id) => {
    if (!id) return;
    setExpandedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      return unique([...prev, id]);
    });
  };

  const onNotificationClick = async (item) => {
    const id = item?.id ?? null;
    if (!id) return;

    const isRead = Boolean(item?.is_read ?? item?.isRead);
    toggleExpanded(id);
    if (!isRead) {
      await markRead(id);
    }
  };

  return (
    <>
      <header className="topbar">
        <h1 className="topbar-title">Уведомления</h1>
        <RefreshButton onClick={() => load({ offset: 0, append: false })} />
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
          sorted.length === 0 ? (
            <div className="empty-state" style={{ marginTop: 18 }}>
              <div className="empty-ico">📭</div>
              <h3>Пока пусто</h3>
              <p>Здесь появятся уведомления об изменениях и записях на тренировки.</p>
            </div>
          ) : (
            <div className="notifications-list">
              {sorted.map((n) => {
                const id = n?.id ?? null;
                const title = normalizeText(n?.title ?? n?.subject) || 'Уведомление';
                const text = normalizeText(n?.message ?? n?.text ?? n?.body);
                const url = normalizeText(n?.url);
                const created = parseDate(n?.created_at ?? n?.createdAt);
                const isRead = Boolean(n?.is_read ?? n?.isRead);
                const isExpanded = id != null && expandedIds.includes(id);

                return (
                  <button
                    key={id ?? `${title}-${created?.toISOString() ?? ''}`}
                    className={`notification-item ${isExpanded ? 'expanded' : ''}`}
                    type="button"
                    onClick={() => onNotificationClick(n)}
                  >
                    <div className="notification-row">
                      <div className="notification-title-wrap">
                        <span className={`notification-dot ${isRead ? 'read' : 'unread'}`} aria-hidden="true" />
                        <span className="notification-title">{title}</span>
                      </div>
                      <span className="notification-date">{formatWhen(created)}</span>
                    </div>

                    <div className={`notification-text ${isExpanded ? 'expanded' : 'collapsed'}`}>
                      {text || formatWhen(created)}
                    </div>

                    {isExpanded && url ? (
                      <div className="notification-link-wrap">
                        <span className="notification-link-label">Ссылка:</span>
                        <a
                          href={url}
                          className="notification-link"
                          onClick={(ev) => {
                            ev.preventDefault();
                            ev.stopPropagation();
                            openExternal(url);
                          }}
                        >
                          {url}
                        </a>
                      </div>
                    ) : null}
                  </button>
                );
              })}

              {canLoadMore ? (
                <div style={{ padding: '10px 2px' }}>
                  <button className="secondary-btn" type="button" onClick={loadMore}>
                    Загрузить ещё
                  </button>
                </div>
              ) : null}
            </div>
          )
        ) : null}
      </div>
    </>
  );
}
