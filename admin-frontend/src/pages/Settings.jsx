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
    label: 'N С‡Р°СЃРѕРІ РґРѕ С‚СЂРµРЅРёСЂРѕРІРєРё: Р·Р°РїСЂРµС‚ РѕС‚РјРµРЅС‹',
    type: 'number',
    defaultValue: '4',
    description: 'Р—Р°РїСЂРµС‚ РѕС‚РјРµРЅС‹ Р·Р°РїРёСЃРё РјРµРЅРµРµ С‡РµРј Р·Р° N С‡Р°СЃРѕРІ РґРѕ РЅР°С‡Р°Р»Р° С‚СЂРµРЅРёСЂРѕРІРєРё.',
  },
  {
    key: 'autoban_hours_before_training',
    label: 'N С‡Р°СЃРѕРІ РґРѕ С‚СЂРµРЅРёСЂРѕРІРєРё: Р°РІС‚РѕР±Р°РЅ Р·Р° РЅРµРѕРїР»Р°С‚Сѓ',
    type: 'number',
    defaultValue: '2',
    description: 'Р§РµСЂРµР· N С‡Р°СЃРѕРІ РґРѕ РЅР°С‡Р°Р»Р° Р·Р°РїСѓСЃРєР°РµС‚СЃСЏ РїСЂРѕРІРµСЂРєР° РЅРµРѕРїР»Р°С‚ Рё Р°РІС‚РѕР±Р°РЅ.',
  },
  {
    key: 'ban_text_default',
    label: 'РўРµРєСЃС‚ Р±Р°РЅР° РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ',
    type: 'textarea',
    defaultValue: 'Р’С‹ РѕРіСЂР°РЅРёС‡РµРЅС‹ РІ Р·Р°РїРёСЃРё РґРѕ РїРѕРіР°С€РµРЅРёСЏ РґРѕР»РіР°.',
    description: 'РўРµРєСЃС‚ РїСЂРµРґСѓРїСЂРµР¶РґРµРЅРёСЏ РІ mini app РїСЂРё Р±Р°РЅРµ/Р°РІС‚РѕР±Р°РЅРµ.',
  },
  {
    key: 'ban_text_debt',
    label: 'РўРµРєСЃС‚ Р±Р°РЅР° Р·Р° РґРѕР»Рі',
    type: 'textarea',
    defaultValue: 'РЈ РІР°СЃ РµСЃС‚СЊ Р·Р°РґРѕР»Р¶РµРЅРЅРѕСЃС‚СЊ. РћРїР»Р°С‚РёС‚Рµ С‚СЂРµРЅРёСЂРѕРІРєСѓ РґР»СЏ СЃРЅСЏС‚РёСЏ РѕРіСЂР°РЅРёС‡РµРЅРёР№.',
    description: 'Р Р°СЃС€РёСЂРµРЅРЅС‹Р№ С‚РµРєСЃС‚ РґР»СЏ СЃР»СѓС‡Р°СЏ Р°РІС‚РѕР±Р°РЅР° РїРѕ РЅРµРѕРїР»Р°С‚Рµ.',
  },
  {
    key: 'payment_provider_key',
    label: '\u042d\u043a\u0432\u0430\u0439\u0440\u0438\u043d\u0433 (YooKassa): shop_id (account_id)',
    type: 'text',
    defaultValue: '',
    description: '\u0418\u0434\u0435\u043d\u0442\u0438\u0444\u0438\u043a\u0430\u0442\u043e\u0440 \u043c\u0430\u0433\u0430\u0437\u0438\u043d\u0430 YooKassa (shop_id/account_id), \u0430 \u043d\u0435 \u043f\u0443\u0431\u043b\u0438\u0447\u043d\u044b\u0439 \u043a\u043b\u044e\u0447.',
  },
  {
    key: 'payment_provider_secret',
    label: '\u042d\u043a\u0432\u0430\u0439\u0440\u0438\u043d\u0433 (YooKassa): secret key',
    type: 'password',
    defaultValue: '',
    description: '\u0421\u0435\u043a\u0440\u0435\u0442\u043d\u044b\u0439 \u043a\u043b\u044e\u0447 YooKassa \u0434\u043b\u044f server-to-server \u0437\u0430\u043f\u0440\u043e\u0441\u043e\u0432.',
  },
  {
    key: 'acquiring_phone_number',
    label: 'Р­РєРІР°Р№СЂРёРЅРі: РЅРѕРјРµСЂ С‚РµР»РµС„РѕРЅР° РґР»СЏ РѕРїР»Р°С‚С‹',
    type: 'text',
    defaultValue: '',
    description: 'РќРѕРјРµСЂ С‚РµР»РµС„РѕРЅР°, РїРѕРєР°Р·С‹РІР°РµРјС‹Р№ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ РїСЂРё РѕРїР»Р°С‚Рµ РїРѕ РЅРѕРјРµСЂСѓ.',
  },
  {
    key: 'payments_enabled',
    label: 'РџСЂРёРµРј РѕРїР»Р°С‚',
    type: 'select',
    options: [
      { value: 'true', label: 'Р’РєР»СЋС‡РµРЅ' },
      { value: 'false', label: 'РћС‚РєР»СЋС‡РµРЅ' },
    ],
    defaultValue: 'true',
    description: 'Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ С„Р»Р°Рі РІРєР»СЋС‡РµРЅРёСЏ/РѕС‚РєР»СЋС‡РµРЅРёСЏ РїСЂРёРµРјР° РѕРїР»Р°С‚.',
  },
    {
    key: 'contacts_text',
    label: 'РўРµРєСЃС‚ СЂР°Р·РґРµР»Р° В«РљРѕРЅС‚Р°РєС‚С‹В» РґР»СЏ Telegram-Р±РѕС‚Р° Рё miniapp',
    type: 'textarea',
    defaultValue: 'РљРѕРЅС‚Р°РєС‚С‹ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°:\nРўРµР»РµС„РѕРЅ: +7 (000) 000-00-00\nTelegram: @elmiravolley',
    description: 'Р•РґРёРЅС‹Р№ С‚РµРєСЃС‚ СЂР°Р·РґРµР»Р° В«РљРѕРЅС‚Р°РєС‚С‹В» РґР»СЏ Р±РѕС‚Р° Рё miniapp.',
  },
  {
    key: 'rules_text',
    label: 'РўРµРєСЃС‚ СЂР°Р·РґРµР»Р° В«РџСЂР°РІРёР»Р°В» РґР»СЏ Telegram-Р±РѕС‚Р° Рё miniapp',
    type: 'textarea',
    defaultValue:
      'РџСЂР°РІРёР»Р° С€РєРѕР»С‹:\n1) РџСЂРёС…РѕРґРёС‚Рµ Р·Р°СЂР°РЅРµРµ.\n2) РЈС‡РёС‚С‹РІР°Р№С‚Рµ СЃСЂРѕРє РѕС‚РјРµРЅС‹.\n3) РЎРѕР±Р»СЋРґР°Р№С‚Рµ СѓРІР°Р¶РёС‚РµР»СЊРЅРѕРµ РѕР±С‰РµРЅРёРµ.',
    description: 'Р•РґРёРЅС‹Р№ С‚РµРєСЃС‚ СЂР°Р·РґРµР»Р° В«РџСЂР°РІРёР»Р°В» РґР»СЏ Р±РѕС‚Р° Рё miniapp.',
  },
  {
    key: 'promotions_text',
    label: 'РўРµРєСЃС‚ СЂР°Р·РґРµР»Р° В«РђРєС†РёРёВ» РґР»СЏ Telegram-Р±РѕС‚Р° Рё miniapp',
    type: 'textarea',
    defaultValue:
      'РђРєС‚СѓР°Р»СЊРЅС‹Рµ Р°РєС†РёРё Рё РїСЂРµРґР»РѕР¶РµРЅРёСЏ:\n1) РЎРєРёРґРєР° РЅР° РїРµСЂРІРѕРµ РїРѕСЃРµС‰РµРЅРёРµ.\n2) Р‘РѕРЅСѓСЃС‹ Р·Р° СЂРµРіСѓР»СЏСЂРЅС‹Рµ С‚СЂРµРЅРёСЂРѕРІРєРё.\n3) РЎРїРµС†РёР°Р»СЊРЅС‹Рµ СѓСЃР»РѕРІРёСЏ РЅР° Р°Р±РѕРЅРµРјРµРЅС‚С‹.',
    description: 'Р•РґРёРЅС‹Р№ С‚РµРєСЃС‚ СЂР°Р·РґРµР»Р° В«РђРєС†РёРёВ» РґР»СЏ Р±РѕС‚Р° Рё miniapp.',
  },

];

const SETTING_KEY_RE = /^[a-z0-9][a-z0-9_.:-]{1,119}$/i;
const PHONE_RE = /^\+?[0-9()\-\s]{6,32}$/;

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
      toast.push(e?.message || 'РћС€РёР±РєР° Р·Р°РіСЂСѓР·РєРё РЅР°СЃС‚СЂРѕРµРє', 'error');
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
    const cancelHours = Number(values.cancel_hours_before_training);
    if (!Number.isInteger(cancelHours) || cancelHours < 0 || cancelHours > 168) {
      toast.push('РџР°СЂР°РјРµС‚СЂ РѕС‚РјРµРЅС‹ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ С†РµР»С‹Рј С‡РёСЃР»РѕРј РѕС‚ 0 РґРѕ 168 С‡Р°СЃРѕРІ', 'error');
      return;
    }

    const autobanHours = Number(values.autoban_hours_before_training);
    if (!Number.isInteger(autobanHours) || autobanHours < 0 || autobanHours > 168) {
      toast.push('РџР°СЂР°РјРµС‚СЂ Р°РІС‚РѕР±Р°РЅР° РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ С†РµР»С‹Рј С‡РёСЃР»РѕРј РѕС‚ 0 РґРѕ 168 С‡Р°СЃРѕРІ', 'error');
      return;
    }

    const paymentsEnabled = String(values.payments_enabled || '').trim().toLowerCase();
    if (paymentsEnabled !== 'true' && paymentsEnabled !== 'false') {
      toast.push('РџРѕР»Рµ "РџСЂРёРµРј РѕРїР»Р°С‚" РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ true РёР»Рё false', 'error');
      return;
    }

    const acquiringPhone = String(values.acquiring_phone_number || '').trim();
    if (acquiringPhone && !PHONE_RE.test(acquiringPhone)) {
      toast.push('РќРѕРјРµСЂ РґР»СЏ РѕРїР»Р°С‚С‹ РёРјРµРµС‚ РЅРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ С„РѕСЂРјР°С‚', 'error');
      return;
    }

    setSaving(true);
    try {
      for (const field of SETTING_FIELDS) {
        await saveKey(field.key, values[field.key], descriptions[field.key] || field.description);
      }
      toast.push('РќР°СЃС‚СЂРѕР№РєРё СЃРѕС…СЂР°РЅРµРЅС‹', 'success');
      await loadSettings();
    } catch (e) {
      toast.push(e?.message || 'РћС€РёР±РєР° СЃРѕС…СЂР°РЅРµРЅРёСЏ РЅР°СЃС‚СЂРѕРµРє', 'error');
    } finally {
      setSaving(false);
    }
  }

  async function onSaveCustom() {
    const key = customKey.trim();
    if (!key) {
      toast.push('РЈРєР°Р¶РёС‚Рµ РєР»СЋС‡ РЅР°СЃС‚СЂРѕР№РєРё', 'error');
      return;
    }

    if (!SETTING_KEY_RE.test(key)) {
      toast.push('РљР»СЋС‡ РЅР°СЃС‚СЂРѕР№РєРё РјРѕР¶РµС‚ СЃРѕРґРµСЂР¶Р°С‚СЊ С‚РѕР»СЊРєРѕ Р±СѓРєРІС‹, С†РёС„СЂС‹, _ . : - (2-120 СЃРёРјРІРѕР»РѕРІ)', 'error');
      return;
    }
    if (String(customValue || '').length > 5000) {
      toast.push('Р—РЅР°С‡РµРЅРёРµ СЃР»РёС€РєРѕРј РґР»РёРЅРЅРѕРµ (РјР°РєСЃРёРјСѓРј 5000 СЃРёРјРІРѕР»РѕРІ)', 'error');
      return;
    }
    if (String(customDescription || '').length > 2000) {
      toast.push('РћРїРёСЃР°РЅРёРµ СЃР»РёС€РєРѕРј РґР»РёРЅРЅРѕРµ (РјР°РєСЃРёРјСѓРј 2000 СЃРёРјРІРѕР»РѕРІ)', 'error');
      return;
    }

    setBusyMap((prev) => ({ ...prev, custom: true }));
    try {
      await saveKey(key, customValue, customDescription || null);
      setCustomKey('');
      setCustomValue('');
      setCustomDescription('');
      toast.push('РџРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєР°СЏ РЅР°СЃС‚СЂРѕР№РєР° СЃРѕС…СЂР°РЅРµРЅР°', 'success');
      await loadSettings();
    } catch (e) {
      toast.push(e?.message || 'РћС€РёР±РєР° СЃРѕС…СЂР°РЅРµРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРѕР№ РЅР°СЃС‚СЂРѕР№РєРё', 'error');
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
      toast.push(`РќР°СЃС‚СЂРѕР№РєР° "${key}" СѓРґР°Р»РµРЅР°`, 'success');
      await loadSettings();
    } catch (e) {
      toast.push(e?.message || 'РћС€РёР±РєР° СѓРґР°Р»РµРЅРёСЏ РЅР°СЃС‚СЂРѕР№РєРё', 'error');
    } finally {
      setBusyMap((prev) => ({ ...prev, [key]: false }));
    }
  }

  return (
    <AdminLayout
      title="РќР°СЃС‚СЂРѕР№РєРё"
      subtitle="Р“Р»РѕР±Р°Р»СЊРЅС‹Рµ РїР°СЂР°РјРµС‚СЂС‹ РїСЂРёР»РѕР¶РµРЅРёСЏ Рё СЌРєРІР°Р№СЂРёРЅРіР°"
      actions={(
        <>
          <Button variant="secondary" onClick={loadSettings} disabled={loading}>РћР±РЅРѕРІРёС‚СЊ</Button>
          <Button onClick={onSaveAll} disabled={saving || loading}>
            {saving ? (
              <span className="inline-flex items-center gap-8"><Spinner size={16} /> РЎРѕС…СЂР°РЅСЏРµРј</span>
            ) : (
              'РЎРѕС…СЂР°РЅРёС‚СЊ РІСЃРµ'
            )}
          </Button>
        </>
      )}
    >
      <Card>
        <div className="section-title">Р“Р»РѕР±Р°Р»СЊРЅС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё</div>

        {loading ? (
          <div className="inline-flex items-center gap-10">
            <Spinner size={18} /> Р—Р°РіСЂСѓР¶Р°РµРј Р·РЅР°С‡РµРЅРёСЏ...
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
        <div className="section-title">Р”РѕР±Р°РІРёС‚СЊ/РѕР±РЅРѕРІРёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєСѓСЋ РЅР°СЃС‚СЂРѕР№РєСѓ</div>
        <div className="grid-3">
          <Field label="РљР»СЋС‡">
            <Input
              value={customKey}
              onChange={(e) => setCustomKey(e.target.value)}
              placeholder="РЅР°РїСЂРёРјРµСЂ: payment_provider_terminal"
            />
          </Field>
          <Field label="Р—РЅР°С‡РµРЅРёРµ">
            <Input value={customValue} onChange={(e) => setCustomValue(e.target.value)} />
          </Field>
          <Field label="РћРїРёСЃР°РЅРёРµ">
            <Input value={customDescription} onChange={(e) => setCustomDescription(e.target.value)} />
          </Field>
        </div>
        <Button onClick={onSaveCustom} disabled={Boolean(busyMap.custom)}>
          {busyMap.custom ? 'РЎРѕС…СЂР°РЅСЏРµРј...' : 'РЎРѕС…СЂР°РЅРёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєСѓСЋ РЅР°СЃС‚СЂРѕР№РєСѓ'}
        </Button>
      </Card>

      <Card>
        <div className="section-title">РўРµРєСѓС‰РёРµ Р·РЅР°С‡РµРЅРёСЏ РёР· API</div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>РљР»СЋС‡</th>
                <th>Р—РЅР°С‡РµРЅРёРµ</th>
                <th>РћРїРёСЃР°РЅРёРµ</th>
                <th>Р”РµР№СЃС‚РІРёСЏ</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.key}>
                  <td>{item.key}</td>
                  <td>{item.value}</td>
                  <td>{item.description || 'вЂ”'}</td>
                  <td>
                    {!knownKeys.has(item.key) ? (
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => onDeleteKey(item.key)}
                        disabled={Boolean(busyMap[item.key])}
                      >
                        {busyMap[item.key] ? '...' : 'РЈРґР°Р»РёС‚СЊ'}
                      </Button>
                    ) : (
                      <span className="muted">РЎРёСЃС‚РµРјРЅР°СЏ</span>
                    )}
                  </td>
                </tr>
              ))}
              {!items.length && !loading ? (
                <tr>
                  <td colSpan={4} className="table-empty">РќР°СЃС‚СЂРѕР№РєРё РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        {extraItems.length ? (
          <div className="muted" style={{ marginTop: 10 }}>
            РџРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёС… РєР»СЋС‡РµР№: <b>{extraItems.length}</b>
          </div>
        ) : null}
      </Card>
    </AdminLayout>
  );
}