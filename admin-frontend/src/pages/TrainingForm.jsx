import { useEffect, useMemo, useState } from 'react';
import AdminLayout from '../components/AdminLayout.jsx';
import Card from '../components/Card.jsx';
import Button from '../components/Button.jsx';
import Spinner from '../components/Spinner.jsx';
import { Field, Input, Select, Textarea } from '../components/Field.jsx';
import { apiDownloadFile, apiFetchJson } from '../lib/api.js';
import { fromDatetimeLocalValue, toDatetimeLocalValue } from '../lib/format.js';
import { navigate } from '../lib/router.js';
import { useToast } from '../components/Toast.jsx';
import { ensureSession, getAdminTokens } from '../lib/adminAuth.js';
import { CANONICAL_LEVEL_NAMES, normalizeLevelName } from '../lib/levels.js';

const MAX_UPLOAD_MB = 50;
const DEFAULT_MIN_LEVEL = CANONICAL_LEVEL_NAMES[0];
const DEFAULT_MAX_LEVEL = CANONICAL_LEVEL_NAMES[CANONICAL_LEVEL_NAMES.length - 1];
const TITLE_RE = /^[\p{L}\p{N}][\p{L}\p{N}\s.,:()"'!?+\-/]{1,99}$/u;
const PERSON_NAME_RE = /^[\p{L}][\p{L}\s.'-]{1,99}$/u;
const LOCATION_RE = /^[\p{L}\p{N}][\p{L}\p{N}\s.,:()"'!?+\-/]{1,119}$/u;
const MEDIA_URL_RE = /^(https?:\/\/[^\s]+|\/media\/trainings\/[^\s]+)$/i;
const AMPLUA_MAIN_CAPACITY_FIXED = 10;

function isAmpluaTrainingType(value) {
  return String(value || '').trim().toLowerCase() === 'амплуа';
}

function resolveTrainingLevelName(value, fallback) {
  return normalizeLevelName(value) || fallback;
}

function normalizeNumber(value, fallback = 0) {
  if (value == null || value === '') return fallback;
  const parsed = Number(String(value).replace(',', '.').trim());
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeMediaUrl(value) {
  const text = String(value || '').trim();
  return text || '';
}

function normalizeMediaUrlList(value) {
  const source = Array.isArray(value) ? value : [value];
  const seen = new Set();
  const result = [];
  source.forEach((item) => {
    const url = normalizeMediaUrl(item);
    if (!url || seen.has(url)) return;
    seen.add(url);
    result.push(url);
  });
  return result;
}

function parseImageUrlsText(value) {
  return normalizeMediaUrlList(
    String(value || '')
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean),
  );
}

function locationLabel(location) {
  const title = location?.name || `Локация #${location?.id ?? '—'}`;
  const details = [location?.metro, location?.address].filter(Boolean).join(' • ');
  return details ? `${title} (${details})` : title;
}

function parseApiError(payload, status) {
  if (!payload) return `HTTP ${status}`;
  if (typeof payload === 'string') return payload;
  if (payload?.error?.message) return String(payload.error.message);
  if (Array.isArray(payload?.error?.details) && payload.error.details.length) {
    const first = payload.error.details[0];
    const loc = Array.isArray(first?.loc) ? first.loc.join('.') : '';
    const msg = first?.msg ? String(first.msg) : '';
    if (loc && msg) return `${loc}: ${msg}`;
    if (msg) return msg;
  }
  if (typeof payload?.detail === 'string') return payload.detail;
  return `HTTP ${status}`;
}

async function uploadTrainingMedia(file) {
  const sizeMb = file.size / (1024 * 1024);
  if (sizeMb > MAX_UPLOAD_MB) {
    throw new Error(`Файл слишком большой: максимум ${MAX_UPLOAD_MB} МБ`);
  }

  const ok = await ensureSession();
  if (!ok) {
    throw new Error('Сессия истекла. Войдите снова.');
  }

  const { accessToken } = getAdminTokens();
  const formData = new FormData();
  formData.append('file', file);

  let response = await fetch('/api/v1/trainings/media', {
    method: 'POST',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    body: formData,
  });

  if (response.status === 401) {
    const refreshed = await ensureSession();
    if (!refreshed) throw new Error('Сессия истекла. Войдите снова.');

    const retryToken = getAdminTokens().accessToken;
    response = await fetch('/api/v1/trainings/media', {
      method: 'POST',
      headers: retryToken ? { Authorization: `Bearer ${retryToken}` } : undefined,
      body: formData,
    });
  }

  const raw = await response.text();
  let payload = null;
  try {
    payload = raw ? JSON.parse(raw) : null;
  } catch {
    payload = raw;
  }

  if (!response.ok) {
    throw new Error(parseApiError(payload, response.status));
  }

  const data = payload?.result || payload;
  const url = data?.url;
  if (!url) {
    throw new Error('Сервер не вернул URL загруженного файла');
  }

  return String(url);
}

export default function TrainingFormPage({ mode, trainingId, routeState }) {
  const toast = useToast();
  const isEdit = mode === 'edit';

  const [busy, setBusy] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const [loading, setLoading] = useState(Boolean(isEdit));

  const [form, setForm] = useState({
    title: '',
    description: '',
    start_at_local: '',
    duration_minutes: 90,
    min_level_name: DEFAULT_MIN_LEVEL,
    max_level_name: DEFAULT_MAX_LEVEL,
    price: 0,
    capacity_main: 12,
    capacity_reserve: 12,
    training_type: '',
    coach_name: '',
    location_name: '',
    image_url: '',
    image_urls_text: '',
    video_url: '',
  });

  const [imageFiles, setImageFiles] = useState([]);
  const [videoFile, setVideoFile] = useState(null);
  const [removeImage, setRemoveImage] = useState(false);
  const [removeVideo, setRemoveVideo] = useState(false);
  const [locations, setLocations] = useState([]);
  const [selectedLocationId, setSelectedLocationId] = useState('');
  const [selectedLocationFallback, setSelectedLocationFallback] = useState('');

  const [errors, setErrors] = useState({});
  const canSave = useMemo(() => !busy && !loading, [busy, loading]);
  const isAmplua = isAmpluaTrainingType(form.training_type);
  const ampluaMainCapacity = AMPLUA_MAIN_CAPACITY_FIXED;

  function setField(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function validate() {
    const nextErrors = {};

    const title = String(form.title || '').trim();
    if (!title) {
      nextErrors.title = 'Введите название тренировки';
    } else if (title.length < 2) {
      nextErrors.title = 'Название должно содержать минимум 2 символа';
    } else if (title.length > 100) {
      nextErrors.title = 'Название слишком длинное (максимум 100 символов)';
    } else if (!TITLE_RE.test(title)) {
      nextErrors.title = 'Название содержит недопустимые символы';
    }

    if (!form.start_at_local) {
      nextErrors.start_at_local = 'Выберите дату и время начала';
    }

    const durationRaw = String(form.duration_minutes ?? '').replace(',', '.').trim();
    const duration = Number(durationRaw);
    if (!durationRaw) {
      nextErrors.duration_minutes = 'Укажите длительность тренировки';
    } else if (!Number.isFinite(duration)) {
      nextErrors.duration_minutes = 'Длительность должна быть числом';
    } else if (!Number.isInteger(duration)) {
      nextErrors.duration_minutes = 'Длительность указывается только в целых минутах';
    } else if (duration < 1) {
      nextErrors.duration_minutes = 'Минимальная длительность — 1 минута';
    } else if (duration > 600) {
      nextErrors.duration_minutes = 'Слишком длинная тренировка: максимум 600 минут';
    }

    const priceRaw = String(form.price ?? '').replace(',', '.').trim();
    const price = Number(priceRaw);
    if (!priceRaw) {
      nextErrors.price = 'Укажите стоимость';
    } else if (!Number.isFinite(price)) {
      nextErrors.price = 'Стоимость должна быть числом';
    } else if (price < 0) {
      nextErrors.price = 'Стоимость не может быть отрицательной';
    } else if (price > 1000000) {
      nextErrors.price = 'Стоимость слишком большая (максимум 1 000 000 ₽)';
    } else if (!/^\d+([.,]\d{1,2})?$/.test(priceRaw)) {
      nextErrors.price = 'Стоимость может содержать максимум 2 знака после запятой';
    }

    if (!isAmplua) {
      const capMainRaw = String(form.capacity_main ?? '').trim();
      const capMain = Number(capMainRaw);
      if (!capMainRaw) {
        nextErrors.capacity_main = 'Укажите вместимость основы';
      } else if (!Number.isFinite(capMain) || !Number.isInteger(capMain)) {
        nextErrors.capacity_main = 'Вместимость основы должна быть целым числом';
      } else if (capMain < 0) {
        nextErrors.capacity_main = 'Вместимость основы не может быть отрицательной';
      } else if (capMain > 1000) {
        nextErrors.capacity_main = 'Слишком большая вместимость основы (максимум 1000)';
      }
    }

    const capReserveRaw = String(form.capacity_reserve ?? '').trim();
    const capReserve = Number(capReserveRaw);
    if (!capReserveRaw) {
      nextErrors.capacity_reserve = 'Укажите вместимость резерва';
    } else if (!Number.isFinite(capReserve) || !Number.isInteger(capReserve)) {
      nextErrors.capacity_reserve = 'Вместимость резерва должна быть целым числом';
    } else if (capReserve < 0) {
      nextErrors.capacity_reserve = 'Вместимость резерва не может быть отрицательной';
    } else if (capReserve > 1000) {
      nextErrors.capacity_reserve = 'Слишком большая вместимость резерва (максимум 1000)';
    }

    const minIndex = CANONICAL_LEVEL_NAMES.indexOf(form.min_level_name);
    const maxIndex = CANONICAL_LEVEL_NAMES.indexOf(form.max_level_name);
    if (minIndex < 0 || maxIndex < 0) {
      nextErrors.min_level_name = 'Выберите уровни из списка';
      nextErrors.max_level_name = 'Выберите уровни из списка';
    } else if (minIndex > maxIndex) {
      nextErrors.min_level_name = 'Минимальный уровень не может быть выше максимального';
      nextErrors.max_level_name = 'Максимальный уровень должен быть не ниже минимального';
    }

    if (!selectedLocationId && !form.location_name.trim()) {
      nextErrors.location_name = 'Выберите локацию из списка или введите новую';
    } else if (!selectedLocationId) {
      const locationName = String(form.location_name || '').trim();
      if (locationName.length > 120) {
        nextErrors.location_name = 'Название локации слишком длинное (максимум 120 символов)';
      } else if (!LOCATION_RE.test(locationName)) {
        nextErrors.location_name = 'Название локации содержит недопустимые символы';
      }
    }

    const coachName = String(form.coach_name || '').trim();
    if (coachName) {
      if (coachName.length > 100) {
        nextErrors.coach_name = 'Имя тренера слишком длинное (максимум 100 символов)';
      } else if (!PERSON_NAME_RE.test(coachName)) {
        nextErrors.coach_name = 'Имя тренера содержит недопустимые символы';
      }
    }

    const description = String(form.description || '');
    if (description.length > 500) {
      nextErrors.description = 'Описание слишком длинное (максимум 500 символов)';
    }

    if (imageFiles.some((file) => !String(file?.type || '').startsWith('image/'))) {
      nextErrors.image_file = 'Загрузите файл изображения (image/*)';
    }
    if (imageFiles.some((file) => Number(file?.size || 0) > MAX_UPLOAD_MB * 1024 * 1024)) {
      nextErrors.image_file = `Изображение слишком большое (максимум ${MAX_UPLOAD_MB} МБ)`;
    }

    if (videoFile && !String(videoFile.type || '').startsWith('video/')) {
      nextErrors.video_file = 'Загрузите видеофайл (video/*)';
    }
    if (videoFile && videoFile.size > MAX_UPLOAD_MB * 1024 * 1024) {
      nextErrors.video_file = `Видео слишком большое (максимум ${MAX_UPLOAD_MB} МБ)`;
    }

    if (!imageFiles.length && form.image_url && !MEDIA_URL_RE.test(String(form.image_url).trim())) {
      nextErrors.image_url = 'Некорректная ссылка на изображение';
    }
    const extraImageUrls = parseImageUrlsText(form.image_urls_text);
    if (extraImageUrls.some((url) => !MEDIA_URL_RE.test(url))) {
      nextErrors.image_urls_text = 'Некорректная ссылка в дополнительных фото';
    }
    if (!videoFile && form.video_url && !MEDIA_URL_RE.test(String(form.video_url).trim())) {
      nextErrors.video_url = 'Некорректная ссылка на видео';
    }

    return nextErrors;
  }

  async function loadLocations() {
    try {
      const res = await apiFetchJson('/locations?limit=500&offset=0&only_with_trainings=false', { auth: true });
      setLocations(res?.items || []);
    } catch {
      // Справочник локаций не критичен: можно ввести локацию вручную.
    }
  }

  async function loadForEdit() {
    const fromState = routeState?.training;
    if (fromState && String(fromState.id) === String(trainingId)) {
      const locationId = fromState.location_id != null ? String(fromState.location_id) : '';
      const locationName = fromState.location_name || '';
      const imageUrls = normalizeMediaUrlList([
        fromState.image_url || '',
        ...(Array.isArray(fromState.image_urls) ? fromState.image_urls : []),
      ]);
      setForm({
        title: fromState.title || '',
        description: fromState.description || '',
        start_at_local: toDatetimeLocalValue(fromState.start_at),
        duration_minutes: fromState.duration_minutes || 90,
        min_level_name: resolveTrainingLevelName(fromState.min_level_name, DEFAULT_MIN_LEVEL),
        max_level_name: resolveTrainingLevelName(fromState.max_level_name, DEFAULT_MAX_LEVEL),
        price: fromState.price ?? 0,
        capacity_main: fromState.capacity_main ?? 0,
        capacity_reserve: fromState.capacity_reserve ?? 0,
        training_type: fromState.training_type || '',
        coach_name: fromState.coach_name || '',
        location_name: locationId ? '' : locationName,
        image_url: imageUrls[0] || '',
        image_urls_text: imageUrls.slice(1).join('\n'),
        video_url: fromState.video_url || '',
      });
      setSelectedLocationId(locationId);
      setSelectedLocationFallback(locationId ? (locationName || `Локация #${locationId}`) : '');
      setLoading(false);
      return;
    }

    try {
      const data = await apiFetchJson(`/trainings/admin/${trainingId}`, { auth: true });
      const locationId = data.location_id != null ? String(data.location_id) : '';
      const locationName = data.location_name || '';
      const imageUrls = normalizeMediaUrlList([
        data.image_url || '',
        ...(Array.isArray(data.image_urls) ? data.image_urls : []),
      ]);
      setForm({
        title: data.title || '',
        description: data.description || '',
        start_at_local: toDatetimeLocalValue(data.start_at),
        duration_minutes: data.duration_minutes || 90,
        min_level_name: resolveTrainingLevelName(data.min_level_name, DEFAULT_MIN_LEVEL),
        max_level_name: resolveTrainingLevelName(data.max_level_name, DEFAULT_MAX_LEVEL),
        price: data.price ?? 0,
        capacity_main: data.capacity_main ?? 0,
        capacity_reserve: data.capacity_reserve ?? 0,
        training_type: data.training_type || '',
        coach_name: data.coach_name || '',
        location_name: locationId ? '' : locationName,
        image_url: imageUrls[0] || '',
        image_urls_text: imageUrls.slice(1).join('\n'),
        video_url: data.video_url || '',
      });
      setSelectedLocationId(locationId);
      setSelectedLocationFallback(locationId ? (locationName || `Локация #${locationId}`) : '');
    } catch {
      toast.push('Не удалось загрузить тренировку для редактирования', 'error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLocations();
  }, []);

  useEffect(() => {
    if (isEdit) loadForEdit();
    else setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEdit, trainingId]);

  async function onSave() {
    const nextErrors = validate();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      toast.push('Проверьте поля формы', 'error');
      return;
    }

    const startAtIso = fromDatetimeLocalValue(form.start_at_local);
    if (!startAtIso) {
      setErrors((prev) => ({ ...prev, start_at_local: 'Некорректная дата/время' }));
      toast.push('Проверьте дату и время', 'error');
      return;
    }

    setBusy(true);
    try {
      let imageUrl = form.image_url || '';
      let videoUrl = form.video_url || '';
      const additionalImageUrls = parseImageUrlsText(form.image_urls_text);

      if (removeImage) imageUrl = '';
      if (removeVideo) videoUrl = '';

      if (imageFiles.length) {
        const uploadedImageUrls = [];
        for (const file of imageFiles) {
          // Загружаем по очереди, чтобы не создавать лишние гонки в API/media.
          const uploaded = await uploadTrainingMedia(file);
          uploadedImageUrls.push(uploaded);
        }
        imageUrl = uploadedImageUrls[0] || '';
        if (uploadedImageUrls.length > 1) {
          additionalImageUrls.unshift(...uploadedImageUrls.slice(1));
        }
      }
      if (videoFile) {
        videoUrl = await uploadTrainingMedia(videoFile);
      }
      const imageUrls = normalizeMediaUrlList([imageUrl, ...additionalImageUrls]);

      const payload = {
        title: form.title.trim(),
        description: form.description || null,
        start_at: startAtIso,
        duration_minutes: Math.max(1, Math.round(normalizeNumber(form.duration_minutes, 90))),
        min_level_name: form.min_level_name || null,
        max_level_name: form.max_level_name || null,
        price: Math.max(0, normalizeNumber(form.price, 0)),
        capacity_main: isAmplua ? ampluaMainCapacity : Math.max(0, Math.round(normalizeNumber(form.capacity_main, 0))),
        capacity_reserve: Math.max(0, Math.round(normalizeNumber(form.capacity_reserve, 0))),
        training_type: isAmplua ? 'амплуа' : null,
        amplua_positions: null,
        coach_name: form.coach_name || null,
        location_id: selectedLocationId ? Number(selectedLocationId) : null,
        location_name: selectedLocationId ? null : (form.location_name.trim() || null),
        image_url: imageUrls[0] || null,
        image_urls: imageUrls.length ? imageUrls : null,
        video_url: videoUrl || null,
      };

      if (isEdit) {
        await apiFetchJson(`/trainings/${trainingId}`, { method: 'PATCH', body: payload, auth: true });
        toast.push('Тренировка обновлена', 'success');
      } else {
        await apiFetchJson('/trainings', { method: 'POST', body: payload, auth: true });
        toast.push('Тренировка создана', 'success');
      }

      navigate('/trainings');
    } catch (e) {
      toast.push(e?.message || 'Ошибка сохранения', 'error');
    } finally {
      setBusy(false);
    }
  }

  async function onExportParticipants() {
    if (!isEdit || !trainingId || exportBusy) return;
    setExportBusy(true);
    try {
      await apiDownloadFile(`/trainings/${trainingId}/participants.xlsx`, {
        auth: true,
        filenameFallback: `training-${trainingId}-participants.xlsx`,
      });
      toast.push('Список участников выгружен', 'success');
    } catch (e) {
      toast.push(e?.message || 'Не удалось выгрузить список участников', 'error');
    } finally {
      setExportBusy(false);
    }
  }

  return (
    <AdminLayout
      title={isEdit ? `Редактирование #${trainingId}` : 'Создание тренировки'}
      subtitle="Заполните поля и сохраните изменения"
      actions={(
        <>
          <Button variant="secondary" onClick={() => navigate('/trainings')} disabled={busy}>Назад</Button>
          {isEdit ? (
            <Button variant="secondary" onClick={onExportParticipants} disabled={busy || loading || exportBusy}>
              {exportBusy ? (
                <span className="inline-flex items-center gap-8"><Spinner size={16} /> Выгружаем</span>
              ) : (
                'Список участников (Excel)'
              )}
            </Button>
          ) : null}
          <Button onClick={onSave} disabled={!canSave}>
            {busy ? (
              <span className="inline-flex items-center gap-8"><Spinner size={16} /> Сохраняем</span>
            ) : (
              'Сохранить'
            )}
          </Button>
        </>
      )}
    >
      <Card className="form">
        {loading ? (
          <div className="inline-flex items-center gap-10">
            <Spinner size={18} /> Загружаем данные...
          </div>
        ) : (
          <div className="grid-2">
            <Field label="Название" error={errors.title}>
              <Input value={form.title} onChange={(e) => setField('title', e.target.value)} />
            </Field>

            <Field label="Дата и время" error={errors.start_at_local}>
              <Input
                type="datetime-local"
                value={form.start_at_local}
                onChange={(e) => setField('start_at_local', e.target.value)}
              />
            </Field>

            <Field label="Длительность, минут" error={errors.duration_minutes}>
              <Input
                type="text"
                inputMode="decimal"
                value={form.duration_minutes}
                onChange={(e) => setField('duration_minutes', e.target.value)}
              />
            </Field>

            <Field label="Стоимость, ₽" error={errors.price}>
              <Input
                type="text"
                inputMode="decimal"
                value={form.price}
                onChange={(e) => setField('price', e.target.value)}
              />
            </Field>

            {isAmplua ? (
              <Field label="Вместимость (основа)">
                <>
                  <Input type="text" inputMode="numeric" value={ampluaMainCapacity} disabled />
                  <div className="field-hint">Фиксировано по правилам ampLua (автоматически на backend).</div>
                </>
              </Field>
            ) : (
              <Field label="Вместимость (основа)" error={errors.capacity_main}>
                <Input
                  type="text"
                  inputMode="numeric"
                  value={form.capacity_main}
                  onChange={(e) => setField('capacity_main', e.target.value)}
                />
              </Field>
            )}

            <Field label="Вместимость (резерв)" error={errors.capacity_reserve}>
              <Input
                type="text"
                inputMode="numeric"
                value={form.capacity_reserve}
                onChange={(e) => setField('capacity_reserve', e.target.value)}
              />
            </Field>

            <Field label="Минимальный уровень" error={errors.min_level_name}>
              <Select value={form.min_level_name} onChange={(e) => setField('min_level_name', e.target.value)}>
                {CANONICAL_LEVEL_NAMES.map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </Select>
            </Field>

            <Field label="Максимальный уровень" error={errors.max_level_name}>
              <Select value={form.max_level_name} onChange={(e) => setField('max_level_name', e.target.value)}>
                {CANONICAL_LEVEL_NAMES.map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </Select>
            </Field>

            <Field label="Тренер" error={errors.coach_name}>
              <Input value={form.coach_name} onChange={(e) => setField('coach_name', e.target.value)} />
            </Field>

            <Field label="Тип тренировки">
              <Select value={form.training_type} onChange={(e) => setField('training_type', e.target.value)}>
                <option value="">Обычная</option>
                <option value="амплуа">амплуа</option>
              </Select>
            </Field>

            {isAmplua ? (
              <Field
                label="Позиции ampLua"
                hint="Позиции Team 1 / Team 2 и слоты назначаются автоматически. Ручная настройка отключена."
              >
                <Input type="text" value="Автоматически по фиксированным правилам" disabled />
              </Field>
            ) : null}

            <Field label="Локация из справочника">
              <Select
                value={selectedLocationId}
                onChange={(e) => {
                  const value = e.target.value;
                  setSelectedLocationId(value);
                  if (value) {
                    setField('location_name', '');
                  }
                }}
              >
                <option value="">Новая локация (ввести вручную)</option>
                {selectedLocationId && selectedLocationFallback && !locations.some((l) => String(l.id) === selectedLocationId) ? (
                  <option value={selectedLocationId}>{selectedLocationFallback}</option>
                ) : null}
                {locations.map((location) => (
                  <option key={location.id} value={String(location.id)}>
                    {locationLabel(location)}
                  </option>
                ))}
              </Select>
            </Field>

            <Field
              label="Новая локация"
              error={errors.location_name}
              hint="Если в списке нет нужной локации, введите название вручную"
            >
              <Input
                value={form.location_name}
                onChange={(e) => setField('location_name', e.target.value)}
                placeholder="Например: Дворец спорта Левобережный"
                disabled={Boolean(selectedLocationId)}
              />
            </Field>

            <Field
              label="Фото тренировки"
              error={errors.image_file}
              hint="Загрузите изображение. Поддерживаются форматы image/*, до 50 МБ"
            >
              <>
                <Input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={(e) => {
                    const files = Array.from(e.target.files || []);
                    setImageFiles(files);
                    if (files.length) setRemoveImage(false);
                  }}
                />
                {imageFiles.length ? (
                  <div className="field-hint">Выбрано файлов: {imageFiles.length}</div>
                ) : null}
                {!imageFiles.length && form.image_url ? (
                  <div className="field-hint">Текущее фото: <a href={form.image_url} target="_blank" rel="noreferrer">открыть</a></div>
                ) : null}
                {(imageFiles.length || form.image_url) ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setImageFiles([]);
                      setRemoveImage(true);
                    }}
                  >
                    Убрать фото
                  </Button>
                ) : null}
              </>
            </Field>

            <Field
              label="Дополнительные фото (URL, по одному в строке)"
              error={errors.image_urls_text}
              hint="Первое фото показывается как основное. Остальные попадут в галерею тренировки."
            >
              <Textarea
                rows={4}
                value={form.image_urls_text}
                onChange={(e) => setField('image_urls_text', e.target.value)}
                placeholder={"/media/trainings/photo-2.jpg\nhttps://example.com/photo-3.jpg"}
              />
            </Field>

            <Field
              label="Видео тренировки"
              error={errors.video_file}
              hint="Загрузите видео. Поддерживаются форматы video/*, до 50 МБ"
            >
              <>
                <Input
                  type="file"
                  accept="video/*"
                  onChange={(e) => {
                    const f = e.target.files?.[0] || null;
                    setVideoFile(f);
                    if (f) setRemoveVideo(false);
                  }}
                />
                {videoFile ? <div className="field-hint">Выбран файл: {videoFile.name}</div> : null}
                {!videoFile && form.video_url ? (
                  <div className="field-hint">Текущее видео: <a href={form.video_url} target="_blank" rel="noreferrer">открыть</a></div>
                ) : null}
                {(videoFile || form.video_url) ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setVideoFile(null);
                      setRemoveVideo(true);
                    }}
                  >
                    Убрать видео
                  </Button>
                ) : null}
              </>
            </Field>

            <Field label="Описание" error={errors.description}>
              <Textarea rows={4} value={form.description} onChange={(e) => setField('description', e.target.value)} />
            </Field>
          </div>
        )}
      </Card>
    </AdminLayout>
  );
}
