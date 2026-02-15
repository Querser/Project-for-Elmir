import { useEffect, useMemo, useRef, useState } from 'react';
import AdminLayout from '../components/AdminLayout.jsx';
import Card from '../components/Card.jsx';
import Button from '../components/Button.jsx';
import Spinner from '../components/Spinner.jsx';
import Modal from '../components/Modal.jsx';
import { Field, Input, Select, Textarea } from '../components/Field.jsx';
import { apiFetchJson } from '../lib/api.js';
import { navigate } from '../lib/router.js';
import { formatDate, formatDateTime, formatMoney, toIsoFromDatetimeLocal } from '../lib/format.js';
import { useToast } from '../components/Toast.jsx';
import { filterCanonicalLevels } from '../lib/levels.js';

const URL_RE = /^https?:\/\/[^\s]+$/i;
const BAN_REASON_RE = /^[\p{L}\p{N}\s.,:;()"'!?+\-/%#@&\u2116]*$/u;

function extractPlainText(html) {
  const raw = String(html || '');
  if (!raw.trim()) return '';
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') {
    return raw.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  }
  const doc = new DOMParser().parseFromString(raw, 'text/html');
  return (doc.body?.textContent || '').replace(/\s+/g, ' ').trim();
}

function sanitizeInlineStyle(styleValue) {
  const raw = String(styleValue || '');
  return raw
    .replace(/expression\s*\([^)]*\)/gi, '')
    .replace(/behavior\s*:[^;]+;?/gi, '')
    .replace(/url\s*\(\s*['"]?\s*javascript:[^)]+\)/gi, '')
    .trim();
}

function sanitizeHtml(html) {
  const raw = String(html || '');
  if (!raw.trim()) return '';

  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') {
    return raw.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '');
  }

  const allowedTags = new Set([
    'a', 'b', 'strong', 'i', 'em', 'u', 's',
    'span', 'div', 'p', 'br',
    'ul', 'ol', 'li',
    'blockquote', 'code', 'pre',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'font',
  ]);
  const allowedAttrs = new Set(['style', 'href', 'target', 'rel', 'title']);

  const doc = new DOMParser().parseFromString(`<div>${raw}</div>`, 'text/html');
  const root = doc.body.firstElementChild;
  if (!root) return '';

  const walk = (node) => {
    const children = Array.from(node.children || []);
    children.forEach(walk);

    const tag = node.tagName?.toLowerCase?.() || '';
    if (!allowedTags.has(tag)) {
      const parent = node.parentNode;
      if (!parent) return;
      while (node.firstChild) {
        parent.insertBefore(node.firstChild, node);
      }
      parent.removeChild(node);
      return;
    }

    Array.from(node.attributes || []).forEach((attr) => {
      const name = attr.name.toLowerCase();
      const value = String(attr.value || '');

      if (name.startsWith('on') || !allowedAttrs.has(name)) {
        node.removeAttribute(attr.name);
        return;
      }

      if (name === 'style') {
        const safe = sanitizeInlineStyle(value);
        if (safe) node.setAttribute('style', safe);
        else node.removeAttribute('style');
        return;
      }

      if (name === 'href') {
        if (!/^(https?:|mailto:|tg:)/i.test(value)) {
          node.removeAttribute('href');
        }
        return;
      }

      if (name === 'target') {
        node.setAttribute('target', '_blank');
        return;
      }

      if (name === 'rel') {
        node.setAttribute('rel', 'noopener noreferrer');
      }
    });

    if (tag === 'a' && node.getAttribute('href')) {
      node.setAttribute('target', '_blank');
      node.setAttribute('rel', 'noopener noreferrer');
    }
  };

  walk(root);
  return root.innerHTML;
}

function isBanActiveNow(ban, nowTs = Date.now()) {
  if (!ban || !ban.active) return false;
  const untilRaw = ban.until;
  if (!untilRaw) return true;
  const untilTs = new Date(untilRaw).getTime();
  if (!Number.isFinite(untilTs)) return false;
  return untilTs >= nowTs;
}

export default function PlayerDetailsPage({ userId }) {
  const toast = useToast();

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState('');

  const [user, setUser] = useState(null);
  const [levels, setLevels] = useState([]);

  const [nextLevelId, setNextLevelId] = useState('');
  const [banReason, setBanReason] = useState('');
  const [banReasonError, setBanReasonError] = useState('');
  const [banUntil, setBanUntil] = useState('');
  const [banModalOpen, setBanModalOpen] = useState(false);
  const [notifyTitle, setNotifyTitle] = useState('Уведомление');
  const [notifyText, setNotifyText] = useState('');
  const [notifyUrl, setNotifyUrl] = useState('');
  const editorRef = useRef(null);

  const activeBan = useMemo(() => {
    const bans = Array.isArray(user?.bans) ? user.bans : [];
    const nowTs = Date.now();
    return bans.find((b) => isBanActiveNow(b, nowTs)) || null;
  }, [user]);
  const hasActiveBan = Boolean(user?.has_active_ban) || Boolean(activeBan);
  const notifyTextPlain = useMemo(() => extractPlainText(notifyText), [notifyText]);

  function syncNotificationEditorValue() {
    const html = editorRef.current?.innerHTML || '';
    setNotifyText(html);
  }

  function clearNotificationEditor() {
    if (editorRef.current) editorRef.current.innerHTML = '';
    setNotifyText('');
  }

  async function loadLevels() {
    try {
      const res = await apiFetchJson('/levels', { auth: true });
      setLevels(filterCanonicalLevels(res?.items || []));
    } catch {
      // Не критично для экрана
    }
  }

  async function loadUser() {
    setLoading(true);
    try {
      const data = await apiFetchJson(`/admin/users/${userId}`, { auth: true });
      setUser(data);
      setNextLevelId(data?.level_id ? String(data.level_id) : '');
    } catch (e) {
      toast.push(e?.message || 'Ошибка загрузки карточки игрока', 'error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLevels();
    loadUser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function onSaveLevel() {
    setActionBusy('level');
    try {
      const payload = { level_id: nextLevelId ? Number(nextLevelId) : null };
      await apiFetchJson(`/admin/users/${userId}/level`, { method: 'PATCH', body: payload, auth: true });
      toast.push('Уровень обновлён', 'success');
      await loadUser();
    } catch (e) {
      toast.push(e?.message || 'Ошибка изменения уровня', 'error');
    } finally {
      setActionBusy('');
    }
  }

  async function onUnban() {
    setActionBusy('unban');
    try {
      await apiFetchJson(`/admin/users/${userId}/unban`, { method: 'POST', auth: true });
      toast.push('Бан снят', 'success');
      await loadUser();
    } catch (e) {
      toast.push(e?.message || 'Ошибка снятия бана', 'error');
    } finally {
      setActionBusy('');
    }
  }

  async function onCancelBannedEnrollments() {
    setActionBusy('cancel_enrollments');
    try {
      const res = await apiFetchJson(`/admin/users/${userId}/cancel-enrollments`, {
        method: 'POST',
        auth: true,
      });
      const cancelled = Number(res?.cancelled || 0);
      if (cancelled > 0) {
        toast.push(`Отменено записей: ${cancelled}`, 'success');
      } else {
        toast.push('Активных записей для отмены не найдено', 'success');
      }
      await loadUser();
    } catch (e) {
      toast.push(e?.message || 'Ошибка отмены записей пользователя', 'error');
    } finally {
      setActionBusy('');
    }
  }

  async function onBanSubmit() {
    const reason = banReason.trim();

    if (!reason) {
      setBanReasonError('Укажите причину бана');
      return;
    }
    if (reason.length < 3) {
      setBanReasonError('Причина бана слишком короткая (минимум 3 символа)');
      return;
    }
    if (reason.length > 500) {
      setBanReasonError('Причина бана слишком длинная (максимум 500 символов)');
      return;
    }
    if (!BAN_REASON_RE.test(reason)) {
      setBanReasonError('Причина бана содержит недопустимые символы');
      return;
    }
    setBanReasonError('');

    setBusy(true);
    try {
      await apiFetchJson(`/admin/users/${userId}/ban`, {
        method: 'POST',
        auth: true,
        body: {
          reason,
          until: banUntil ? toIsoFromDatetimeLocal(banUntil) : null,
        },
      });
      setBanModalOpen(false);
      setBanReason('');
      setBanReasonError('');
      setBanUntil('');
      toast.push('Бан установлен', 'success');
      await loadUser();
    } catch (e) {
      toast.push(e?.message || 'Ошибка установки бана', 'error');
    } finally {
      setBusy(false);
    }
  }

  async function onMarkPaidOffline(debtId) {
    setActionBusy(`debt_${debtId}`);
    try {
      await apiFetchJson(`/admin/users/${userId}/debts/${debtId}/mark-paid`, {
        method: 'POST',
        auth: true,
      });
      toast.push('Оплата отмечена, долг закрыт', 'success');
      await loadUser();
    } catch (e) {
      toast.push(e?.message || 'Ошибка отметки оплаты', 'error');
    } finally {
      setActionBusy('');
    }
  }

  async function onSendNotificationToUser() {
    const cleanTitle = notifyTitle.trim() || 'Уведомление';
    const sourceText = editorRef.current?.innerHTML ?? notifyText;
    const cleanText = sanitizeHtml(sourceText);
    const cleanTextPlain = extractPlainText(cleanText);
    const cleanUrl = notifyUrl.trim();

    if (!cleanTextPlain) {
      toast.push('Введите текст уведомления', 'error');
      return;
    }
    if (cleanTitle.length > 120) {
      toast.push('Заголовок слишком длинный (максимум 120 символов)', 'error');
      return;
    }
    if (cleanTextPlain.length > 4000) {
      toast.push('Текст слишком длинный (максимум 4000 символов)', 'error');
      return;
    }
    if (cleanUrl && !URL_RE.test(cleanUrl)) {
      toast.push('Ссылка должна начинаться с http:// или https://', 'error');
      return;
    }

    setActionBusy('notify');
    try {
      await apiFetchJson('/admin/notifications/users', {
        method: 'POST',
        auth: true,
        body: {
          user_ids: [Number(userId)],
          type: 'SYSTEM',
          title: cleanTitle,
          text: cleanText,
          url: cleanUrl || null,
        },
      });
      toast.push('Уведомление отправлено', 'success');
      clearNotificationEditor();
      setNotifyUrl('');
    } catch (e) {
      toast.push(e?.message || 'Ошибка отправки уведомления', 'error');
    } finally {
      setActionBusy('');
    }
  }

  const fullName = [user?.last_name, user?.first_name].filter(Boolean).join(' ') || `Игрок #${userId}`;

  return (
    <AdminLayout
      title={`Игрок: ${fullName}`}
      subtitle="Профиль, история, долги и баны"
      actions={(
        <>
          <Button variant="secondary" onClick={() => navigate('/players')}>К списку</Button>
          <Button variant="secondary" onClick={loadUser} disabled={loading}>Обновить</Button>
        </>
      )}
    >
      {loading ? (
        <Card>
          <div className="inline-flex items-center gap-10">
            <Spinner size={18} /> Загружаем карточку игрока...
          </div>
        </Card>
      ) : null}

      {!loading && user ? (
        <>
          <Card>
            <div className="section-title">Общая информация</div>
            <div className="kv-grid">
              <div><span className="muted">ID:</span> <b>{user.id}</b></div>
              <div><span className="muted">Telegram ID:</span> <b>{user.telegram_id}</b></div>
              <div><span className="muted">Username:</span> <b>@{user.username || '—'}</b></div>
              <div><span className="muted">Телефон:</span> <b>{user.phone || '—'}</b></div>
              <div><span className="muted">Пол:</span> <b>{user.gender || '—'}</b></div>
              <div><span className="muted">Дата рождения:</span> <b>{formatDate(user.birth_date)}</b></div>
              <div><span className="muted">Рейтинг:</span> <b>{Number(user.rating || 0)}</b></div>
              <div><span className="muted">Кубки:</span> <b>{Number(user.cups || 0)}</b></div>
              <div>
                <span className="muted">Текущий уровень:</span>{' '}
                <b>{user.level_name || 'Не назначен'}</b>
              </div>
              <div>
                <span className="muted">Статус:</span>{' '}
                {hasActiveBan ? <span className="badge badge-danger">В бане</span> : <span className="badge">Активен</span>}
              </div>
            </div>
          </Card>

          <Card>
            <div className="section-title">Действия администратора</div>
            <div className="grid-2">
              <Field label="Изменить уровень">
                <Select value={nextLevelId} onChange={(e) => setNextLevelId(e.target.value)}>
                  <option value="">Не назначен</option>
                  {levels.map((l) => (
                    <option key={l.id} value={String(l.id)}>{l.name || `#${l.id}`}</option>
                  ))}
                </Select>
              </Field>

              <div className="field">
                <div className="field-label">Сохранение</div>
                <div className="field-control">
                  <Button onClick={onSaveLevel} disabled={actionBusy === 'level'}>
                    {actionBusy === 'level' ? (
                      <span className="inline-flex items-center gap-8"><Spinner size={14} /> Сохраняем</span>
                    ) : (
                      'Сохранить уровень'
                    )}
                  </Button>
                </div>
              </div>
            </div>

            <div className="inline-flex gap-8" style={{ marginTop: 14 }}>
              <Button
                variant="danger"
                onClick={() => {
                  setBanReasonError('');
                  setBanModalOpen(true);
                }}
              >
                Установить бан
              </Button>
              <Button variant="secondary" onClick={onUnban} disabled={actionBusy === 'unban'}>
                {actionBusy === 'unban' ? 'Снимаем...' : 'Снять бан'}
              </Button>
              {hasActiveBan ? (
                <Button
                  variant="secondary"
                  onClick={onCancelBannedEnrollments}
                  disabled={actionBusy === 'cancel_enrollments'}
                >
                  {actionBusy === 'cancel_enrollments'
                    ? 'Отменяем записи...'
                    : 'Отменить все записи на тренировки'}
                </Button>
              ) : null}
            </div>

            <div className="muted" style={{ marginTop: 10 }}>
              {hasActiveBan
                ? `Активный бан: ${activeBan?.reason || 'Причина не указана'} ${activeBan?.until ? `(до ${formatDateTime(activeBan.until)})` : '(без срока)'}` 
                : 'Активного бана нет'}
            </div>
            <div className="section-title" style={{ marginTop: 18 }}>Персональное уведомление</div>
            <div className="grid-2">
              <Field label="Заголовок">
                <Input
                  value={notifyTitle}
                  onChange={(e) => setNotifyTitle(e.target.value)}
                  placeholder="Уведомление"
                />
              </Field>

              <Field label="Ссылка (опционально)">
                <Input
                  value={notifyUrl}
                  onChange={(e) => setNotifyUrl(e.target.value)}
                  placeholder="https://..."
                />
              </Field>
            </div>

            <Field label="Текст уведомления">
              <div className="rich-editor-wrap">
                <div
                  ref={editorRef}
                  className="rich-editor"
                  contentEditable
                  role="textbox"
                  aria-multiline="true"
                  data-placeholder="Текст уведомления для игрока..."
                  suppressContentEditableWarning
                  onInput={syncNotificationEditorValue}
                  onBlur={syncNotificationEditorValue}
                />
              </div>
              <div className="field-hint">
                Лимит: 4000 символов текста. Сейчас: {notifyTextPlain.length}.
              </div>
            </Field>

            <Button onClick={onSendNotificationToUser} disabled={actionBusy === 'notify'}>
              {actionBusy === 'notify' ? (
                <span className="inline-flex items-center gap-8"><Spinner size={14} /> Отправляем</span>
              ) : (
                'Отправить уведомление игроку'
              )}
            </Button>
          </Card>

          <Card>
            <div className="section-title">Текущие долги</div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>ID долга</th>
                    <th>Тренировка</th>
                    <th>Сумма</th>
                    <th>Создан</th>
                    <th>Действие</th>
                  </tr>
                </thead>
                <tbody>
                  {(user.current_debts || []).map((debt) => (
                    <tr key={debt.id}>
                      <td>{debt.id}</td>
                      <td>#{debt.training_id}</td>
                      <td>{formatMoney(debt.amount)}</td>
                      <td>{formatDateTime(debt.created_at)}</td>
                      <td>
                        <Button
                          size="sm"
                          onClick={() => onMarkPaidOffline(debt.id)}
                          disabled={actionBusy === `debt_${debt.id}`}
                        >
                          {actionBusy === `debt_${debt.id}` ? '...' : 'Отметить оплату'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {!user.current_debts?.length ? (
                    <tr>
                      <td colSpan={5} className="table-empty">Открытых долгов нет</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <div className="section-title">История тренировок</div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Дата/время</th>
                    <th>Тренировка</th>
                    <th>Статус</th>
                    <th>Резерв</th>
                    <th>Оплата</th>
                  </tr>
                </thead>
                <tbody>
                  {(user.training_history || []).map((item) => (
                    <tr key={item.enrollment_id}>
                      <td>{formatDateTime(item.training_start_at)}</td>
                      <td>{item.training_title || `Тренировка #${item.training_id}`}</td>
                      <td>{item.status}</td>
                      <td>{item.is_reserve ? 'Да' : 'Нет'}</td>
                      <td>{item.is_paid ? 'Оплачено' : 'Не оплачено'}</td>
                    </tr>
                  ))}
                  {!user.training_history?.length ? (
                    <tr>
                      <td colSpan={5} className="table-empty">История тренировок пуста</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <div className="section-title">История банов</div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Тип</th>
                    <th>Причина</th>
                    <th>Активен</th>
                    <th>Создан</th>
                    <th>До</th>
                  </tr>
                </thead>
                <tbody>
                  {(user.bans || []).map((ban) => (
                    <tr key={ban.id}>
                      <td>{ban.id}</td>
                      <td>{ban.type}</td>
                      <td>{ban.reason}</td>
                      <td>{ban.active ? 'Да' : 'Нет'}</td>
                      <td>{formatDateTime(ban.created_at)}</td>
                      <td>{formatDateTime(ban.until)}</td>
                    </tr>
                  ))}
                  {!user.bans?.length ? (
                    <tr>
                      <td colSpan={6} className="table-empty">Баны отсутствуют</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      ) : null}

      {banModalOpen ? (
        <Modal
          title="Установить бан игроку"
          onClose={() => {
            setBanReasonError('');
            setBanModalOpen(false);
          }}
          actions={(
            <>
              <Button
                variant="secondary"
                onClick={() => {
                  setBanReasonError('');
                  setBanModalOpen(false);
                }}
                disabled={busy}
              >
                Отмена
              </Button>
              <Button variant="danger" onClick={onBanSubmit} disabled={busy}>
                {busy ? 'Сохраняем...' : 'Установить бан'}
              </Button>
            </>
          )}
        >
          <div className="grid-2">
            <Field label="Причина бана" error={banReasonError}>
              <Textarea
                value={banReason}
                onChange={(e) => {
                  setBanReason(e.target.value);
                  if (banReasonError) {
                    setBanReasonError('');
                  }
                }}
                rows={3}
                placeholder="Например: задолженность за оффлайн оплату"
              />
            </Field>

            <Field label="Срок бана (опционально)">
              <Input type="datetime-local" value={banUntil} onChange={(e) => setBanUntil(e.target.value)} />
            </Field>
          </div>
        </Modal>
      ) : null}
    </AdminLayout>
  );
}
