import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api';

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

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(null);

  const LIMIT = 50;

  const load = async (opts = {}) => {
    const { offset = 0, append = false } = opts;
    try {
      setLoading(true);
      setError('');
      const data = await apiFetch(`/api/v1/notifications?offset=${offset}&limit=${LIMIT}`);
      const next = normalizeItems(data);
      setTotal(typeof data?.total === 'number' ? data.total : null);
      setItems((prev) => (append ? [...prev, ...next] : next));
    } catch (err) {
      setError(err?.message || 'Не удалось загрузить уведомления');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError('');
        const data = await apiFetch(`/api/v1/notifications?offset=0&limit=${LIMIT}`);
        if (cancelled) return;
        setTotal(typeof data?.total === 'number' ? data.total : null);
        setItems(normalizeItems(data));
      } catch (err) {
        if (cancelled) return;
        setError(err?.message || 'Не удалось загрузить уведомления');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const sorted = useMemo(() => {
    const arr = [...items];
    arr.sort((a, b) => {
      const da = parseDate(a?.created_at ?? a?.createdAt)?.getTime() ?? 0;
      const db = parseDate(b?.created_at ?? b?.createdAt)?.getTime() ?? 0;
      return db - da;
    });
    return arr;
  }, [items]);

  const markRead = async (id) => {
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
      await load({ offset: 0, append: false });
    }
  };

  const canLoadMore = useMemo(() => {
    if (loading) return false;
    if (total == null) return false;
    return items.length < total;
  }, [items.length, total, loading]);

  const loadMore = async () => {
    if (!canLoadMore) return;
    await load({ offset: items.length, append: true });
  };

  return (
    <>
      <header className="topbar">
        <h1 className="topbar-title">Уведомления</h1>
        <div style={{ width: 36 }} />
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
            <div className="settings-list" style={{ marginTop: 10 }}>
              {sorted.map((n) => {
                const id = n?.id ?? null;
                const title = n?.title ?? n?.subject ?? 'Уведомление';
                const text = n?.message ?? n?.text ?? n?.body ?? '';
                const created = parseDate(n?.created_at ?? n?.createdAt);
                const isRead = Boolean(n?.is_read ?? n?.isRead);

                return (
                  <div
                    key={id ?? `${title}-${created?.toISOString() ?? ''}`}
                    className="settings-item"
                    role="button"
                    tabIndex={0}
                    onClick={() => markRead(id)}
                  >
                    <div className="settings-item-left">
                      <div className="settings-icon" style={{ background: isRead ? '#f3f4f6' : '#eff6ff' }}>
                        {isRead ? '🔔' : '🟦'}
                      </div>
                      <div>
                        <div className="settings-label">{title}</div>
                        <div className="settings-value">{text ? text : formatWhen(created)}</div>
                      </div>
                    </div>
                    <div className="settings-value">{formatWhen(created)}</div>
                  </div>
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
