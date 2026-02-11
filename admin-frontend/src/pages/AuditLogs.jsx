import { useEffect, useMemo, useState } from 'react';
import AdminLayout from '../components/AdminLayout.jsx';
import Card from '../components/Card.jsx';
import Button from '../components/Button.jsx';
import Spinner from '../components/Spinner.jsx';
import { Field, Input, Select } from '../components/Field.jsx';
import { apiFetchJson } from '../lib/api.js';
import { formatDateTime, toIsoFromDatetimeLocal } from '../lib/format.js';
import { useToast } from '../components/Toast.jsx';

const EVENT_TYPES = [
  '',
  'ENROLL',
  'CANCEL',
  'BAN',
  'UNBAN',
  'PAYMENT',
  'ADMIN_SET_USER_LEVEL',
  'ADMIN_BAN_USER',
  'ADMIN_UNBAN_USER',
  'ADMIN_MARK_DEBT_PAID_OFFLINE',
  'ADMIN_NOTIFICATION_BROADCAST',
  'ADMIN_NOTIFICATION_USERS',
  'ADMIN_NOTIFICATION_TRAINING',
  'ADMIN_SETTING_UPSERT',
  'ADMIN_SETTING_DELETE',
];

function formatData(value) {
  if (!value) return '—';
  try {
    const json = JSON.stringify(value);
    return json.length > 120 ? `${json.slice(0, 117)}...` : json;
  } catch {
    return String(value);
  }
}

export default function AuditLogsPage() {
  const toast = useToast();

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(25);
  const [offset, setOffset] = useState(0);

  const [userId, setUserId] = useState('');
  const [action, setAction] = useState('');
  const [entity, setEntity] = useState('');
  const [entityId, setEntityId] = useState('');
  const [trainingId, setTrainingId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const [busy, setBusy] = useState(false);

  const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
  const pages = useMemo(() => Math.max(1, Math.ceil(total / limit)), [total, limit]);

  async function load() {
    setBusy(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', String(limit));
      params.set('offset', String(offset));
      if (userId.trim()) params.set('user_id', userId.trim());
      if (action.trim()) params.set('action', action.trim());
      if (entity.trim()) params.set('entity', entity.trim());
      if (entityId.trim()) params.set('entity_id', entityId.trim());
      if (trainingId.trim()) params.set('training_id', trainingId.trim());
      if (dateFrom) params.set('date_from', toIsoFromDatetimeLocal(dateFrom));
      if (dateTo) params.set('date_to', toIsoFromDatetimeLocal(dateTo));

      const res = await apiFetchJson(`/admin/audit-logs?${params.toString()}`, { auth: true });
      setItems(res?.items || []);
      setTotal(Number(res?.total || 0));
    } catch (e) {
      toast.push(e?.message || 'Ошибка загрузки журнала действий', 'error');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit, offset, userId, action, entity, entityId, trainingId, dateFrom, dateTo]);

  return (
    <AdminLayout
      title="Журнал действий"
      subtitle="Логи событий системы и действий администратора"
      actions={(
        <Button variant="secondary" onClick={load} disabled={busy}>
          {busy ? (
            <span className="inline-flex items-center gap-8"><Spinner size={16} /> Загрузка</span>
          ) : (
            'Обновить'
          )}
        </Button>
      )}
    >
      <Card className="filters">
        <div className="grid-3">
          <Field label="Пользователь (ID)">
            <Input value={userId} onChange={(e) => { setOffset(0); setUserId(e.target.value); }} placeholder="12" />
          </Field>

          <Field label="Тип события">
            <Select value={action} onChange={(e) => { setOffset(0); setAction(e.target.value); }}>
              {EVENT_TYPES.map((v) => (
                <option key={v || '_all'} value={v}>{v || 'Все'}</option>
              ))}
            </Select>
          </Field>

          <Field label="Тренировка (ID)">
            <Input
              value={trainingId}
              onChange={(e) => { setOffset(0); setTrainingId(e.target.value); }}
              placeholder="ID тренировки"
            />
          </Field>

          <Field label="Entity">
            <Input value={entity} onChange={(e) => { setOffset(0); setEntity(e.target.value); }} placeholder="user / training / debt" />
          </Field>

          <Field label="Entity ID">
            <Input value={entityId} onChange={(e) => { setOffset(0); setEntityId(e.target.value); }} placeholder="ID сущности" />
          </Field>

          <Field label="Лимит на странице">
            <Select value={String(limit)} onChange={(e) => { setOffset(0); setLimit(Number(e.target.value)); }}>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </Select>
          </Field>

          <Field label="Дата от">
            <Input type="datetime-local" value={dateFrom} onChange={(e) => { setOffset(0); setDateFrom(e.target.value); }} />
          </Field>

          <Field label="Дата до">
            <Input type="datetime-local" value={dateTo} onChange={(e) => { setOffset(0); setDateTo(e.target.value); }} />
          </Field>
        </div>
      </Card>

      <Card>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Дата</th>
                <th>Пользователь</th>
                <th>Событие</th>
                <th>Сущность</th>
                <th>Данные</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{formatDateTime(row.created_at)}</td>
                  <td>{row.user_id ?? '—'}</td>
                  <td>{row.action}</td>
                  <td>{row.entity ? `${row.entity}${row.entity_id ? ` #${row.entity_id}` : ''}` : '—'}</td>
                  <td>{formatData(row.data)}</td>
                </tr>
              ))}
              {!items.length && !busy ? (
                <tr>
                  <td colSpan={6} className="table-empty">Записи не найдены</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>

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
