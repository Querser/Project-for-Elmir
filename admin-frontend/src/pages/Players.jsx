import { useEffect, useMemo, useState } from 'react';
import AdminLayout from '../components/AdminLayout.jsx';
import Card from '../components/Card.jsx';
import Button from '../components/Button.jsx';
import Spinner from '../components/Spinner.jsx';
import { Field, Input, Select } from '../components/Field.jsx';
import { apiFetchJson } from '../lib/api.js';
import { navigate } from '../lib/router.js';
import { useToast } from '../components/Toast.jsx';

export default function PlayersPage() {
  const toast = useToast();

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [levels, setLevels] = useState([]);

  const [q, setQ] = useState('');
  const [userIdFilter, setUserIdFilter] = useState('');
  const [levelId, setLevelId] = useState('');
  const [banFilter, setBanFilter] = useState('');

  const [limit, setLimit] = useState(25);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);

  const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
  const pages = useMemo(() => Math.max(1, Math.ceil(total / limit)), [total, limit]);

  async function loadLevels() {
    try {
      const res = await apiFetchJson('/levels', { auth: true });
      setLevels(res?.items || []);
    } catch {
      // Не блокируем экран, если справочник уровней временно недоступен.
    }
  }

  async function loadUsers() {
    setBusy(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', String(limit));
      params.set('offset', String(offset));
      if (q.trim()) params.set('q', q.trim());
      const idFilter = userIdFilter.trim();
      if (/^\d+$/.test(idFilter)) params.set('user_id', idFilter);
      if (levelId) params.set('level_id', levelId);
      if (banFilter === 'banned') params.set('is_banned', 'true');
      if (banFilter === 'not_banned') params.set('is_banned', 'false');

      const res = await apiFetchJson(`/admin/users?${params.toString()}`, { auth: true });
      setItems(res?.items || []);
      setTotal(Number(res?.total || 0));
    } catch (e) {
      toast.push(e?.message || 'Ошибка загрузки игроков', 'error');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadLevels();
  }, []);

  useEffect(() => {
    loadUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, userIdFilter, levelId, banFilter, limit, offset]);

  return (
    <AdminLayout
      title="Игроки"
      subtitle="Пользователи, уровень, долги и баны"
      actions={(
        <>
          <Button variant="secondary" onClick={loadUsers} disabled={busy}>
            {busy ? (
              <span className="inline-flex items-center gap-8">
                <Spinner size={16} /> Загрузка
              </span>
            ) : (
              'Обновить'
            )}
          </Button>
        </>
      )}
    >
      <Card className="filters">
        <div className="grid-3">
          <Field label="Поиск">
            <Input
              value={q}
              onChange={(e) => {
                setOffset(0);
                setQ(e.target.value);
              }}
              placeholder="Имя, username, телефон, telegram_id"
            />
          </Field>

          <Field label="Поиск по ID">
            <Input
              value={userIdFilter}
              onChange={(e) => {
                setOffset(0);
                setUserIdFilter(e.target.value);
              }}
              placeholder="Например: 123"
            />
          </Field>

          <Field label="Уровень">
            <Select
              value={levelId}
              onChange={(e) => {
                setOffset(0);
                setLevelId(e.target.value);
              }}
            >
              <option value="">Все</option>
              {levels.map((l) => (
                <option key={l.id} value={String(l.id)}>
                  {l.name || `#${l.id}`}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Бан">
            <Select
              value={banFilter}
              onChange={(e) => {
                setOffset(0);
                setBanFilter(e.target.value);
              }}
            >
              <option value="">Все</option>
              <option value="banned">Только в бане</option>
              <option value="not_banned">Только без бана</option>
            </Select>
          </Field>

          <Field label="Лимит на странице">
            <Select
              value={String(limit)}
              onChange={(e) => {
                setOffset(0);
                setLimit(Number(e.target.value));
              }}
            >
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </Select>
          </Field>
        </div>
      </Card>

      <div className="list">
        {items.map((user) => {
          const fullName = [user.last_name, user.first_name].filter(Boolean).join(' ') || `Игрок #${user.id}`;
          return (
            <Card key={user.id} className="row">
              <div className="row-main">
                <div className="row-title">
                  {fullName}
                  {user.has_active_ban ? <span className="badge badge-danger">Бан</span> : null}
                </div>

                <div className="row-meta">
                  <span>ID: {user.id}</span>
                  <span>@{user.username || '—'}</span>
                  <span>Телефон: {user.phone || '—'}</span>
                </div>

                <div className="row-meta">
                  <span>
                    Уровень: <b>{user.level_name || 'Не назначен'}</b>
                  </span>
                  <span>
                    Открытых долгов: <b>{Number(user.open_debts_count || 0)}</b>
                  </span>
                </div>
              </div>

              <div className="row-actions">
                <Button variant="secondary" onClick={() => navigate(`/players/${user.id}`)}>
                  Карточка
                </Button>
              </div>
            </Card>
          );
        })}

        {!items.length && !busy ? (
          <Card>
            <div className="muted">Игроки по выбранным фильтрам не найдены.</div>
          </Card>
        ) : null}
      </div>

      <Card className="pager">
        <div className="muted">
          Всего: <b>{total}</b> • Страница <b>{page}</b> / <b>{pages}</b>
        </div>
        <div className="pager-actions">
          <Button
            variant="secondary"
            disabled={offset === 0 || busy}
            onClick={() => setOffset((v) => Math.max(0, v - limit))}
          >
            Назад
          </Button>
          <Button
            variant="secondary"
            disabled={offset + limit >= total || busy}
            onClick={() => setOffset((v) => v + limit)}
          >
            Вперёд
          </Button>
        </div>
      </Card>
    </AdminLayout>
  );
}
