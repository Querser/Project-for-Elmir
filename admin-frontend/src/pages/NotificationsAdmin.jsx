import { useEffect, useMemo, useRef, useState } from 'react';
import AdminLayout from '../components/AdminLayout.jsx';
import Card from '../components/Card.jsx';
import Button from '../components/Button.jsx';
import Spinner from '../components/Spinner.jsx';
import { Field, Input, Select } from '../components/Field.jsx';
import { apiFetchJson } from '../lib/api.js';
import { formatDateTime, toIsoFromDatetimeLocal } from '../lib/format.js';
import { useToast } from '../components/Toast.jsx';

const SEND_MODES = [
  { value: 'broadcast', label: 'Всем пользователям' },
  { value: 'training', label: 'Участникам тренировки' },
  { value: 'users', label: 'Выбранным пользователям' },
];

const NOTIFICATION_TYPES = ['INFO', 'SYSTEM', 'TRAINING', 'IMPORTANT'];
const URL_RE = /^https?:\/\/[^\s]+$/i;

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
  const editorRef = useRef(null);

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
  const textPlain = useMemo(() => extractPlainText(text), [text]);

  function syncEditorValue() {
    const html = editorRef.current?.innerHTML || '';
    setText(html);
  }

  function applyEditorCommand(command) {
    try {
      editorRef.current?.focus();
      document.execCommand(command, false, null);
      syncEditorValue();
    } catch {
      // ignore editor command failures in unsupported webviews
    }
  }

  function clearEditor() {
    if (editorRef.current) editorRef.current.innerHTML = '';
    setText('');
  }

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
    clearEditor();
    setUrl('');
    setTrainingId('');
    setRecipientQuery('');
    setRecipientResults([]);
    setSelectedUserIds([]);
  }

  async function onSend() {
    const cleanTitle = title.trim() || 'Уведомление';
    const sourceText = editorRef.current?.innerHTML ?? text;
    const cleanText = sanitizeHtml(sourceText);
    const cleanTextPlain = extractPlainText(cleanText);
    const cleanUrl = url.trim();

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

    const trainingIdNum = Number(trainingId);
    if (mode === 'training' && (!Number.isInteger(trainingIdNum) || trainingIdNum <= 0)) {
      toast.push('Укажите корректный ID тренировки (целое число > 0)', 'error');
      return;
    }
    if (mode === 'users' && !selectedUserIds.length) {
      toast.push('Выберите хотя бы одного получателя', 'error');
      return;
    }
    if (mode === 'users') {
      const invalidUserId = selectedUserIds.some((id) => !Number.isInteger(Number(id)) || Number(id) <= 0);
      if (invalidUserId) {
        toast.push('В списке получателей есть некорректный ID пользователя', 'error');
        return;
      }
    }

    if (!NOTIFICATION_TYPES.includes(type)) {
      toast.push('Выберите корректный тип уведомления', 'error');
      return;
    }

    setSendBusy(true);
    try {
      if (mode === 'broadcast') {
        await apiFetchJson('/admin/notifications/broadcast', {
          method: 'POST',
          auth: true,
          body: { type, title: cleanTitle, text: cleanText, url: cleanUrl || null },
        });
      } else if (mode === 'training') {
        await apiFetchJson('/admin/notifications/training', {
          method: 'POST',
          auth: true,
          body: {
            training_id: trainingIdNum,
            type,
            title: cleanTitle,
            text: cleanText,
            url: cleanUrl || null,
          },
        });
      } else {
        await apiFetchJson('/admin/notifications/users', {
          method: 'POST',
          auth: true,
          body: {
            user_ids: selectedUserIds,
            type,
            title: cleanTitle,
            text: cleanText,
            url: cleanUrl || null,
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
          <div className="rich-editor-wrap">
            <div className="rich-editor-toolbar">
              <button
                type="button"
                className="rich-editor-btn"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => applyEditorCommand('bold')}
                title="Жирный"
              >
                B
              </button>
              <button
                type="button"
                className="rich-editor-btn"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => applyEditorCommand('italic')}
                title="Курсив"
              >
                I
              </button>
              <button
                type="button"
                className="rich-editor-btn"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => applyEditorCommand('underline')}
                title="Подчеркнутый"
              >
                U
              </button>
              <button
                type="button"
                className="rich-editor-btn"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => applyEditorCommand('insertUnorderedList')}
                title="Список"
              >
                • List
              </button>
              <button
                type="button"
                className="rich-editor-btn"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => applyEditorCommand('insertOrderedList')}
                title="Нумерованный список"
              >
                1. List
              </button>
              <button
                type="button"
                className="rich-editor-btn"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => applyEditorCommand('removeFormat')}
                title="Очистить формат"
              >
                Clear
              </button>
            </div>

            <div
              ref={editorRef}
              className="rich-editor"
              contentEditable
              role="textbox"
              aria-multiline="true"
              data-placeholder="Текст уведомления..."
              suppressContentEditableWarning
              onInput={syncEditorValue}
              onBlur={syncEditorValue}
            />
          </div>
          <div className="field-hint">
            Можно вставлять форматированный текст (шрифты, стили, списки). Лимит: 4000 символов текста.
            Сейчас: {textPlain.length}.
          </div>
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
                  <td>
                    <div
                      className="admin-notification-text"
                      dangerouslySetInnerHTML={{ __html: sanitizeHtml(n.text || '') }}
                    />
                  </td>
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
