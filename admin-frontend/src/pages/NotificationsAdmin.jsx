import { useEffect, useMemo, useState } from 'react';
import AdminLayout from '../components/AdminLayout.jsx';
import Card from '../components/Card.jsx';
import Button from '../components/Button.jsx';
import Spinner from '../components/Spinner.jsx';
import { Field, Input, Select, Textarea } from '../components/Field.jsx';
import { apiFetchJson } from '../lib/api.js';
import { formatDateTime, toIsoFromDatetimeLocal } from '../lib/format.js';
import { useToast } from '../components/Toast.jsx';

const SEND_MODES = [
  { value: 'broadcast', label: 'Всем пользователям' },
  { value: 'training', label: 'Участникам тренировки' },
  { value: 'users', label: 'Выбранным пользователям' },
];

const NOTIFICATION_TYPES = ['INFO', 'SYSTEM', 'TRAINING', 'IMPORTANT'];

export default function NotificationsAdminPage() {
  const toast = useToast();

  const [sendBusy, setSendBusy] = useState(false);
  const [listBusy, setListBusy] = useState(false);

  const [mode, setMode] = useState('broadcast');
  const [type, setType] = useState('INFO');
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [trainingId, setTrainingId] = useState('');

  const [recipientQuery, setRecipientQuery] = useState('');
  const [recipientBusy, setRecipientBusy] = useState(false);
  const [recipientResults, setRecipientResults] = useState([]);
  const [selectedUserIds, setSelectedUserIds] = useState([]);

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(25);
  const [offset, setOffset] = useState(0);
  const [filterType, setFilterType] = useState('');
  const [filterQ, setFilterQ] = useState('');
  const [filterUserId, setFilterUserId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
  const pages = useMemo(() => Math.max(1, Math.ceil(total / limit)), [total, limit]);

  async function searchRecipients() {
    if (!recipientQuery.trim()) {
      setRecipientResults([]);
      return;
    }

    setRecipientBusy(true);
    try {
      const params = new URLSearchParams();
      params.set('q', recipientQuery.trim());
      params.set('limit', '30');
      params.set('offset', '0');
      const res = await apiFetchJson(`/admin/users?${params.toString()}`, { auth: true });
      setRecipientResults(res?.items || []);
    } catch (e) {
      toast.push(e?.message || 'Ошибка поиска получателей', 'error');
    } finally {
      setRecipientBusy(false);
    }
  }

  function toggleUser(userId) {
    setSelectedUserIds((prev) => (
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    ));
  }

  function resetForm() {
    setMode('broadcast');
    setType('INFO');
    setTitle('');
    setText('');
    setUrl('');
    setTrainingId('');
    setRecipientQuery('');
    setRecipientResults([]);
    setSelectedUserIds([]);
  }

  async function onSend() {
    if (!text.trim()) {
      toast.push('Введите текст уведомления', 'error');
      return;
    }
    if (mode === 'training' && !trainingId) {
      toast.push('Укажите ID тренировки', 'error');
      return;
    }
    if (mode === 'users' && !selectedUserIds.length) {
      toast.push('Выберите хотя бы одного получателя', 'error');
      return;
    }

    setSendBusy(true);
    try {
      if (mode === 'broadcast') {
        await apiFetchJson('/admin/notifications/broadcast', {
          method: 'POST',
          auth: true,
          body: { type, title: title.trim() || 'Уведомление', text: text.trim(), url: url.trim() || null },
        });
      } else if (mode === 'training') {
        await apiFetchJson('/admin/notifications/training', {
          method: 'POST',
          auth: true,
          body: {
            training_id: Number(trainingId),
            type,
            title: title.trim() || 'Уведомление',
            text: text.trim(),
            url: url.trim() || null,
          },
        });
      } else {
        await apiFetchJson('/admin/notifications/users', {
          method: 'POST',
          auth: true,
          body: {
            user_ids: selectedUserIds,
            type,
            title: title.trim() || 'Уведомление',
            text: text.trim(),
            url: url.trim() || null,
          },
        });
      }

      toast.push('Уведомление отправлено', 'success');
      resetForm();
      await loadSent();
    } catch (e) {
      toast.push(e?.message || 'Ошибка отправки уведомления', 'error');
    } finally {
      setSendBusy(false);
    }
  }

  async function loadSent() {
    setListBusy(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', String(limit));
      params.set('offset', String(offset));
      if (filterType) params.set('type', filterType);
      if (filterQ.trim()) params.set('q', filterQ.trim());
      if (filterUserId.trim()) params.set('user_id', filterUserId.trim());
      if (dateFrom) params.set('date_from', toIsoFromDatetimeLocal(dateFrom));
      if (dateTo) params.set('date_to', toIsoFromDatetimeLocal(dateTo));

      const res = await apiFetchJson(`/admin/notifications/sent?${params.toString()}`, { auth: true });
      setItems(res?.items || []);
      setTotal(Number(res?.total || 0));
    } catch (e) {
      toast.push(e?.message || 'Ошибка загрузки уведомлений', 'error');
    } finally {
      setListBusy(false);
    }
  }

  useEffect(() => {
    loadSent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit, offset, filterType, filterQ, filterUserId, dateFrom, dateTo]);

  return (
    <AdminLayout
      title="Уведомления"
      subtitle="Создание рассылок и история отправок"
      actions={(
        <Button variant="secondary" onClick={loadSent} disabled={listBusy}>
          {listBusy ? (
            <span className="inline-flex items-center gap-8"><Spinner size={16} /> Загрузка</span>
          ) : (
            'Обновить'
          )}
        </Button>
      )}
    >
      <Card>
        <div className="section-title">Создать уведомление</div>

        <div className="grid-3">
          <Field label="Получатели">
            <Select value={mode} onChange={(e) => setMode(e.target.value)}>
              {SEND_MODES.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </Select>
          </Field>

          <Field label="Тип">
            <Select value={type} onChange={(e) => setType(e.target.value)}>
              {NOTIFICATION_TYPES.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </Select>
          </Field>

          {mode === 'training' ? (
            <Field label="ID тренировки">
              <Input type="number" min="1" value={trainingId} onChange={(e) => setTrainingId(e.target.value)} />
            </Field>
          ) : null}
        </div>

        <div className="grid-2">
          <Field label="Заголовок">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Уведомление" />
          </Field>
          <Field label="Ссылка (опционально)">
            <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." />
          </Field>
        </div>

        <Field label="Текст">
          <Textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} placeholder="Текст уведомления..." />
        </Field>

        {mode === 'users' ? (
          <div className="target-users">
            <div className="grid-2">
              <Field label="Поиск получателей">
                <Input
                  value={recipientQuery}
                  onChange={(e) => setRecipientQuery(e.target.value)}
                  placeholder="Имя, username, телефон"
                />
              </Field>
              <div className="field">
                <div className="field-label">Действия</div>
                <div className="field-control">
                  <Button variant="secondary" onClick={searchRecipients} disabled={recipientBusy}>
                    {recipientBusy ? 'Ищем...' : 'Найти игроков'}
                  </Button>
                </div>
              </div>
            </div>

            {recipientResults.length ? (
              <div className="recipient-list">
                {recipientResults.map((u) => {
                  const checked = selectedUserIds.includes(u.id);
                  const fullName = [u.last_name, u.first_name].filter(Boolean).join(' ') || `Игрок #${u.id}`;
                  return (
                    <label key={u.id} className={`recipient-row ${checked ? 'active' : ''}`}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleUser(u.id)}
                      />
                      <span>{fullName} (@{u.username || '—'})</span>
                    </label>
                  );
                })}
              </div>
            ) : null}

            <div className="muted">Выбрано получателей: <b>{selectedUserIds.length}</b></div>
          </div>
        ) : null}

        <div className="inline-flex gap-8" style={{ marginTop: 12 }}>
          <Button onClick={onSend} disabled={sendBusy}>
            {sendBusy ? 'Отправляем...' : 'Отправить уведомление'}
          </Button>
          <Button variant="secondary" onClick={resetForm} disabled={sendBusy}>Очистить форму</Button>
        </div>
      </Card>

      <Card className="filters">
        <div className="section-title">Отправленные уведомления</div>
        <div className="grid-3">
          <Field label="Поиск">
            <Input
              value={filterQ}
              onChange={(e) => { setOffset(0); setFilterQ(e.target.value); }}
              placeholder="Заголовок/текст"
            />
          </Field>

          <Field label="Тип">
            <Select value={filterType} onChange={(e) => { setOffset(0); setFilterType(e.target.value); }}>
              <option value="">Все</option>
              {NOTIFICATION_TYPES.map((v) => <option key={v} value={v}>{v}</option>)}
            </Select>
          </Field>

          <Field label="ID пользователя">
            <Input
              value={filterUserId}
              onChange={(e) => { setOffset(0); setFilterUserId(e.target.value); }}
              placeholder="Например: 12"
            />
          </Field>

          <Field label="Дата от">
            <Input type="datetime-local" value={dateFrom} onChange={(e) => { setOffset(0); setDateFrom(e.target.value); }} />
          </Field>

          <Field label="Дата до">
            <Input type="datetime-local" value={dateTo} onChange={(e) => { setOffset(0); setDateTo(e.target.value); }} />
          </Field>

          <Field label="Лимит на странице">
            <Select value={String(limit)} onChange={(e) => { setOffset(0); setLimit(Number(e.target.value)); }}>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </Select>
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
                <th>Тип</th>
                <th>Пользователь</th>
                <th>Заголовок</th>
                <th>Текст</th>
              </tr>
            </thead>
            <tbody>
              {items.map((n) => (
                <tr key={n.id}>
                  <td>{n.id}</td>
                  <td>{formatDateTime(n.created_at)}</td>
                  <td>{n.type}</td>
                  <td>#{n.user_id}</td>
                  <td>{n.title}</td>
                  <td>{n.text}</td>
                </tr>
              ))}
              {!items.length && !listBusy ? (
                <tr>
                  <td colSpan={6} className="table-empty">Уведомления не найдены</td>
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
            disabled={offset === 0 || listBusy}
            onClick={() => setOffset((v) => Math.max(0, v - limit))}
          >
            Назад
          </Button>
          <Button
            variant="secondary"
            disabled={offset + limit >= total || listBusy}
            onClick={() => setOffset((v) => v + limit)}
          >
            Вперёд
          </Button>
        </div>
      </Card>
    </AdminLayout>
  );
}
