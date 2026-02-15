import { useEffect, useMemo, useState } from 'react';
import AdminLayout from '../components/AdminLayout.jsx';
import Card from '../components/Card.jsx';
import Button from '../components/Button.jsx';
import Spinner from '../components/Spinner.jsx';
import { Field, Input, Select } from '../components/Field.jsx';
import { apiFetchJson } from '../lib/api.js';
import { formatDateTime, toIsoFromDatetimeLocal } from '../lib/format.js';
import { navigate } from '../lib/router.js';
import { useToast } from '../components/Toast.jsx';
import { ConfirmModal } from '../components/Modal.jsx';

export default function TrainingsPage() {
  const toast = useToast();

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);

  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(25);

  const [q, setQ] = useState('');
  const [coachName, setCoachName] = useState('');
  const [locationId, setLocationId] = useState('');
  const [isCancelled, setIsCancelled] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [order, setOrder] = useState('asc');
  const [locations, setLocations] = useState([]);

  const [confirm, setConfirm] = useState(null);

  const page = useMemo(() => Math.floor(skip / limit) + 1, [skip, limit]);
  const pages = useMemo(() => Math.max(1, Math.ceil(total / limit)), [total, limit]);

  async function loadLocations() {
    try {
      const res = await apiFetchJson('/locations?limit=500&offset=0&only_with_trainings=false', { auth: true });
      setLocations(res?.items || []);
    } catch {
      // список локаций не критичен для рендера страницы
    }
  }

  async function load() {
    setBusy(true);
    try {
      const params = new URLSearchParams();
      params.set('skip', String(skip));
      params.set('limit', String(limit));
      if (q.trim()) params.set('q', q.trim());
      if (coachName.trim()) params.set('coach_name', coachName.trim());
      if (locationId) params.set('location_id', locationId);
      if (isCancelled === 'true') params.set('is_cancelled', 'true');
      if (isCancelled === 'false') params.set('is_cancelled', 'false');
      if (dateFrom) params.set('date_from', toIsoFromDatetimeLocal(dateFrom));
      if (dateTo) params.set('date_to', toIsoFromDatetimeLocal(dateTo));
      params.set('order', order === 'desc' ? 'desc' : 'asc');

      const res = await apiFetchJson(`/trainings/admin?${params.toString()}`, { auth: true });
      setItems(res?.items || []);
      setTotal(Number(res?.total || 0));
    } catch (e) {
      toast.push(e?.message || 'Ошибка загрузки тренировок', 'error');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadLocations();
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skip, limit, q, coachName, locationId, isCancelled, dateFrom, dateTo, order]);

  function openEdit(training) {
    navigate(`/trainings/${training.id}`, { state: { training } });
  }

  function openCreate() {
    navigate('/trainings/new');
  }

  async function doCancel(training) {
    setConfirm(null);
    try {
      await apiFetchJson(`/trainings/${training.id}/cancel`, { method: 'POST', auth: true });
      toast.push('Тренировка отменена', 'success');
      await load();
    } catch (e) {
      toast.push(e?.message || 'Ошибка отмены тренировки', 'error');
    }
  }

  async function doRestore(training) {
    setConfirm(null);
    try {
      await apiFetchJson(`/trainings/${training.id}/restore`, { method: 'POST', auth: true });
      toast.push('Тренировка восстановлена', 'success');
      await load();
    } catch (e) {
      toast.push(e?.message || 'Ошибка восстановления тренировки', 'error');
    }
  }

  async function doDelete(training) {
    setConfirm(null);
    try {
      await apiFetchJson(`/trainings/${training.id}`, { method: 'DELETE', auth: true });
      toast.push('Тренировка удалена', 'success');
      await load();
    } catch (e) {
      toast.push(e?.message || 'Ошибка удаления тренировки', 'error');
    }
  }

  return (
    <AdminLayout
      title="Тренировки"
      subtitle="Управление расписанием"
      actions={(
        <>
          <Button variant="secondary" onClick={load} disabled={busy}>Обновить</Button>
          <Button onClick={openCreate}>Создать</Button>
        </>
      )}
    >
      <Card className="filters">
        <div className="grid-3">
          <Field label="Поиск">
            <Input
              value={q}
              onChange={(e) => { setSkip(0); setQ(e.target.value); }}
              placeholder="Название, описание, тренер"
            />
          </Field>

          <Field label="Тренер">
            <Input
              value={coachName}
              onChange={(e) => { setSkip(0); setCoachName(e.target.value); }}
              placeholder="Иванов"
            />
          </Field>

          <Field label="Локация">
            <Select value={locationId} onChange={(e) => { setSkip(0); setLocationId(e.target.value); }}>
              <option value="">Все</option>
              {locations.map((location) => (
                <option key={location.id} value={String(location.id)}>
                  {location.name ? location.name : `Локация #${location.id}`}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Дата от">
            <Input
              type="datetime-local"
              value={dateFrom}
              onChange={(e) => { setSkip(0); setDateFrom(e.target.value); }}
            />
          </Field>

          <Field label="Дата до">
            <Input
              type="datetime-local"
              value={dateTo}
              onChange={(e) => { setSkip(0); setDateTo(e.target.value); }}
            />
          </Field>

          <Field label="Статус">
            <Select value={isCancelled} onChange={(e) => { setSkip(0); setIsCancelled(e.target.value); }}>
              <option value="">Все</option>
              <option value="false">Активные</option>
              <option value="true">Отменённые</option>
            </Select>
          </Field>

          <Field label="Сортировка">
            <Select value={order} onChange={(e) => { setSkip(0); setOrder(e.target.value); }}>
              <option value="asc">Сначала ближайшие</option>
              <option value="desc">Сначала дальние</option>
            </Select>
          </Field>

          <Field label="Лимит на странице">
            <Select value={String(limit)} onChange={(e) => { setSkip(0); setLimit(Number(e.target.value)); }}>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </Select>
          </Field>

          <div className="field">
            <div className="field-label">Обновить</div>
            <div className="field-control">
              <Button variant="secondary" onClick={load} disabled={busy}>
                {busy ? (
                  <span className="inline-flex items-center gap-8">
                    <Spinner size={16} /> Загрузка
                  </span>
                ) : (
                  'Перезагрузить'
                )}
              </Button>
            </div>
          </div>
        </div>
      </Card>

      <div className="list">
        {items.map((training) => {
          const mainCap = Number(training.capacity_main || 0);
          const reserveCap = Number(training.capacity_reserve || 0);
          const occupiedMain = Number(training.occupied_main || 0);
          const occupiedReserve = Number(training.occupied_reserve || 0);

          return (
            <Card key={training.id} className={`row ${training.is_cancelled ? 'row-cancelled' : ''}`}>
              <div className="row-main">
                <div className="row-title">
                  {training.title || `Тренировка #${training.id}`}
                  {training.is_cancelled ? <span className="badge badge-danger">Отменена</span> : null}
                </div>

                <div className="row-meta">
                  <span>{formatDateTime(training.start_at)}</span>
                  <span>Тренер: {training.coach_name || '-'}</span>
                  <span>
                    Локация: {training.location_name || (training.location_id ? `#${training.location_id}` : '-')}
                  </span>
                  <span>Цена: {training.price ?? 0} ₽</span>
                </div>

                <div className="row-meta">
                  <span>Основа: <b>{occupiedMain}</b> / {mainCap}</span>
                  <span>Резерв: <b>{occupiedReserve}</b> / {reserveCap}</span>
                </div>
              </div>

              <div className="row-actions">
                <Button variant="secondary" onClick={() => openEdit(training)}>Редактировать</Button>

                {!training.is_cancelled ? (
                  <Button variant="danger" onClick={() => setConfirm({ type: 'cancel', training })}>
                    Отменить
                  </Button>
                ) : (
                  <Button variant="secondary" onClick={() => setConfirm({ type: 'restore', training })}>
                    Восстановить
                  </Button>
                )}

                <Button variant="danger" onClick={() => setConfirm({ type: 'delete', training })}>
                  Удалить
                </Button>
              </div>
            </Card>
          );
        })}

        {!items.length && !busy ? (
          <Card>
            <div className="muted">Нет тренировок по выбранным фильтрам.</div>
            <div style={{ marginTop: 10 }}>
              <Button onClick={openCreate}>Создать тренировку</Button>
            </div>
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
            disabled={skip === 0 || busy}
            onClick={() => setSkip((value) => Math.max(0, value - limit))}
          >
            Назад
          </Button>
          <Button
            variant="secondary"
            disabled={skip + limit >= total || busy}
            onClick={() => setSkip((value) => value + limit)}
          >
            Вперёд
          </Button>
        </div>
      </Card>

      {confirm ? (
        <ConfirmModal
          title={
            confirm.type === 'cancel'
              ? 'Отменить тренировку'
              : confirm.type === 'restore'
                ? 'Восстановить тренировку'
                : 'Удалить тренировку'
          }
          text={
            confirm.type === 'cancel'
              ? 'Вы уверены, что хотите отменить тренировку?'
              : confirm.type === 'restore'
                ? 'Вы уверены, что хотите вернуть тренировку в активный статус?'
                : 'Вы уверены, что хотите удалить тренировку? Это действие необратимо.'
          }
          onCancel={() => setConfirm(null)}
          onConfirm={() => (
            confirm.type === 'cancel'
              ? doCancel(confirm.training)
              : confirm.type === 'restore'
                ? doRestore(confirm.training)
                : doDelete(confirm.training)
          )}
          confirmText={
            confirm.type === 'cancel'
              ? 'Отменить'
              : confirm.type === 'restore'
                ? 'Восстановить'
                : 'Удалить'
          }
        />
      ) : null}
    </AdminLayout>
  );
}
