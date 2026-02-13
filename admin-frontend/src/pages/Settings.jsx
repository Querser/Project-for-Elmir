import { useEffect, useMemo, useState } from 'react';
import AdminLayout from '../components/AdminLayout.jsx';
import Card from '../components/Card.jsx';
import Button from '../components/Button.jsx';
import Spinner from '../components/Spinner.jsx';
import { Field, Input, Select, Textarea } from '../components/Field.jsx';
import { apiFetchJson } from '../lib/api.js';
import { useToast } from '../components/Toast.jsx';

const SETTING_FIELDS = [
  {
    key: 'cancel_hours_before_training',
    label: 'N часов до тренировки: запрет отмены',
    type: 'number',
    defaultValue: '4',
    description: 'Запрет отмены записи менее чем за N часов до начала тренировки.',
  },
  {
    key: 'autoban_hours_before_training',
    label: 'N часов до тренировки: автобан за неоплату',
    type: 'number',
    defaultValue: '2',
    description: 'Через N часов до начала запускается проверка неоплат и автобан.',
  },
  {
    key: 'ban_text_default',
    label: 'Текст бана по умолчанию',
    type: 'textarea',
    defaultValue: 'Вы ограничены в записи до погашения долга.',
    description: 'Текст предупреждения в mini app при бане/автобане.',
  },
  {
    key: 'ban_text_debt',
    label: 'Текст бана за долг',
    type: 'textarea',
    defaultValue: 'У вас есть задолженность. Оплатите тренировку для снятия ограничений.',
    description: 'Расширенный текст для случая автобана по неоплате.',
  },
  {
    key: 'payment_provider_key',
    label: 'Эквайринг: публичный ключ / merchant key',
    type: 'text',
    defaultValue: '',
    description: 'Ключ интеграции с платежным провайдером.',
  },
  {
    key: 'payment_provider_secret',
    label: 'Эквайринг: secret',
    type: 'password',
    defaultValue: '',
    description: 'Секрет платежного провайдера.',
  },
  {
    key: 'acquiring_phone_number',
    label: 'Эквайринг: номер телефона для оплаты',
    type: 'text',
    defaultValue: '',
    description: 'Номер телефона, показываемый пользователю при оплате по номеру.',
  },
  {
    key: 'payments_enabled',
    label: 'Прием оплат',
    type: 'select',
    options: [
      { value: 'true', label: 'Включен' },
      { value: 'false', label: 'Отключен' },
    ],
    defaultValue: 'true',
    description: 'Глобальный флаг включения/отключения приема оплат.',
  },
    {
    key: 'contacts_text',
    label: 'Текст раздела «Контакты» для Telegram-бота и miniapp',
    type: 'textarea',
    defaultValue: 'Контакты администратора:\nТелефон: +7 (000) 000-00-00\nTelegram: @elmiravolley',
    description: 'Единый текст раздела «Контакты» для бота и miniapp.',
  },
  {
    key: 'rules_text',
    label: 'Текст раздела «Правила» для Telegram-бота и miniapp',
    type: 'textarea',
    defaultValue:
      'Правила школы:\n1) Приходите заранее.\n2) Учитывайте срок отмены.\n3) Соблюдайте уважительное общение.',
    description: 'Единый текст раздела «Правила» для бота и miniapp.',
  },
  {
    key: 'promotions_text',
    label: 'Текст раздела «Акции» для Telegram-бота и miniapp',
    type: 'textarea',
    defaultValue:
      'Актуальные акции и предложения:\n1) Скидка на первое посещение.\n2) Бонусы за регулярные тренировки.\n3) Специальные условия на абонементы.',
    description: 'Единый текст раздела «Акции» для бота и miniapp.',
  },

];

export default function SettingsPage() {
  const toast = useToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyMap, setBusyMap] = useState({});

  const [items, setItems] = useState([]);
  const [values, setValues] = useState({});
  const [descriptions, setDescriptions] = useState({});

  const [customKey, setCustomKey] = useState('');
  const [customValue, setCustomValue] = useState('');
  const [customDescription, setCustomDescription] = useState('');

  const knownKeys = useMemo(() => new Set(SETTING_FIELDS.map((f) => f.key)), []);
  const extraItems = useMemo(
    () => items.filter((item) => !knownKeys.has(item.key)),
    [items, knownKeys]
  );

  function setFieldValue(key, value) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function loadSettings() {
    setLoading(true);
    try {
      const res = await apiFetchJson('/admin/settings?limit=500&offset=0', { auth: true });
      const rows = res?.items || [];
      setItems(rows);

      const valuesMap = {};
      const descMap = {};
      rows.forEach((item) => {
        valuesMap[item.key] = String(item.value ?? '');
        descMap[item.key] = item.description || '';
      });

      SETTING_FIELDS.forEach((field) => {
        if (!(field.key in valuesMap)) {
          valuesMap[field.key] = field.defaultValue;
        }
        if (!(field.key in descMap)) {
          descMap[field.key] = field.description;
        }
      });

      setValues(valuesMap);
      setDescriptions(descMap);
    } catch (e) {
      toast.push(e?.message || 'Ошибка загрузки настроек', 'error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saveKey(key, value, description) {
    await apiFetchJson(`/admin/settings/${encodeURIComponent(key)}`, {
      method: 'PUT',
      auth: true,
      body: {
        value: String(value ?? ''),
        description: description || null,
      },
    });
  }

  async function onSaveAll() {
    setSaving(true);
    try {
      for (const field of SETTING_FIELDS) {
        await saveKey(field.key, values[field.key], descriptions[field.key] || field.description);
      }
      toast.push('Настройки сохранены', 'success');
      await loadSettings();
    } catch (e) {
      toast.push(e?.message || 'Ошибка сохранения настроек', 'error');
    } finally {
      setSaving(false);
    }
  }

  async function onSaveCustom() {
    const key = customKey.trim();
    if (!key) {
      toast.push('Укажите ключ настройки', 'error');
      return;
    }

    setBusyMap((prev) => ({ ...prev, custom: true }));
    try {
      await saveKey(key, customValue, customDescription || null);
      setCustomKey('');
      setCustomValue('');
      setCustomDescription('');
      toast.push('Пользовательская настройка сохранена', 'success');
      await loadSettings();
    } catch (e) {
      toast.push(e?.message || 'Ошибка сохранения пользовательской настройки', 'error');
    } finally {
      setBusyMap((prev) => ({ ...prev, custom: false }));
    }
  }

  async function onDeleteKey(key) {
    setBusyMap((prev) => ({ ...prev, [key]: true }));
    try {
      await apiFetchJson(`/admin/settings/${encodeURIComponent(key)}`, {
        method: 'DELETE',
        auth: true,
      });
      toast.push(`Настройка "${key}" удалена`, 'success');
      await loadSettings();
    } catch (e) {
      toast.push(e?.message || 'Ошибка удаления настройки', 'error');
    } finally {
      setBusyMap((prev) => ({ ...prev, [key]: false }));
    }
  }

  return (
    <AdminLayout
      title="Настройки"
      subtitle="Глобальные параметры приложения и эквайринга"
      actions={(
        <>
          <Button variant="secondary" onClick={loadSettings} disabled={loading}>Обновить</Button>
          <Button onClick={onSaveAll} disabled={saving || loading}>
            {saving ? (
              <span className="inline-flex items-center gap-8"><Spinner size={16} /> Сохраняем</span>
            ) : (
              'Сохранить все'
            )}
          </Button>
        </>
      )}
    >
      <Card>
        <div className="section-title">Глобальные настройки</div>

        {loading ? (
          <div className="inline-flex items-center gap-10">
            <Spinner size={18} /> Загружаем значения...
          </div>
        ) : (
          <div className="grid-2">
            {SETTING_FIELDS.map((field) => (
              <Field key={field.key} label={field.label} hint={field.description}>
                {field.type === 'textarea' ? (
                  <Textarea
                    rows={3}
                    value={values[field.key] ?? ''}
                    onChange={(e) => setFieldValue(field.key, e.target.value)}
                  />
                ) : null}

                {field.type === 'select' ? (
                  <Select
                    value={values[field.key] ?? ''}
                    onChange={(e) => setFieldValue(field.key, e.target.value)}
                  >
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </Select>
                ) : null}

                {field.type !== 'textarea' && field.type !== 'select' ? (
                  <Input
                    type={field.type === 'password' ? 'password' : field.type === 'number' ? 'number' : 'text'}
                    min={field.type === 'number' ? '0' : undefined}
                    value={values[field.key] ?? ''}
                    onChange={(e) => setFieldValue(field.key, e.target.value)}
                  />
                ) : null}
              </Field>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <div className="section-title">Добавить/обновить пользовательскую настройку</div>
        <div className="grid-3">
          <Field label="Ключ">
            <Input
              value={customKey}
              onChange={(e) => setCustomKey(e.target.value)}
              placeholder="например: payment_provider_terminal"
            />
          </Field>
          <Field label="Значение">
            <Input value={customValue} onChange={(e) => setCustomValue(e.target.value)} />
          </Field>
          <Field label="Описание">
            <Input value={customDescription} onChange={(e) => setCustomDescription(e.target.value)} />
          </Field>
        </div>
        <Button onClick={onSaveCustom} disabled={Boolean(busyMap.custom)}>
          {busyMap.custom ? 'Сохраняем...' : 'Сохранить пользовательскую настройку'}
        </Button>
      </Card>

      <Card>
        <div className="section-title">Текущие значения из API</div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Ключ</th>
                <th>Значение</th>
                <th>Описание</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.key}>
                  <td>{item.key}</td>
                  <td>{item.value}</td>
                  <td>{item.description || '—'}</td>
                  <td>
                    {!knownKeys.has(item.key) ? (
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => onDeleteKey(item.key)}
                        disabled={Boolean(busyMap[item.key])}
                      >
                        {busyMap[item.key] ? '...' : 'Удалить'}
                      </Button>
                    ) : (
                      <span className="muted">Системная</span>
                    )}
                  </td>
                </tr>
              ))}
              {!items.length && !loading ? (
                <tr>
                  <td colSpan={4} className="table-empty">Настройки отсутствуют</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        {extraItems.length ? (
          <div className="muted" style={{ marginTop: 10 }}>
            Пользовательских ключей: <b>{extraItems.length}</b>
          </div>
        ) : null}
      </Card>
    </AdminLayout>
  );
}
