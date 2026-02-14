import { ADMIN_AUTH_PREFIX } from '../config.js';
import {
  getAdminTokens,
  isAccessTokenValid,
  adminRefresh,
  clearAdminTokens,
} from './adminAuth.js';
import { navigate } from './router.js';

const FIELD_LABELS = {
  // Trainings
  title: 'Название',
  description: 'Описание',
  start_at: 'Дата и время начала',
  duration_minutes: 'Длительность',
  price: 'Стоимость',
  capacity_main: 'Вместимость основы',
  capacity_reserve: 'Вместимость резерва',
  min_level_name: 'Минимальный уровень',
  max_level_name: 'Максимальный уровень',
  coach_name: 'Тренер',
  location_name: 'Локация',
  location_id: 'Локация',
  image_url: 'Ссылка на изображение',
  video_url: 'Ссылка на видео',

  // Notifications
  text: 'Текст',
  type: 'Тип',
  url: 'Ссылка',
  user_ids: 'Получатели',
  training_id: 'ID тренировки',

  // Users/Bans
  reason: 'Причина',
  until: 'Срок бана',
  level_id: 'Уровень',

  // Auth
  username: 'Логин',
  password: 'Пароль',
  refresh_token: 'Refresh token',

  // Settings
  key: 'Ключ настройки',
  value: 'Значение',
  cancel_hours_before_training: 'Часы до запрета отмены',
  autoban_hours_before_training: 'Часы до автобана',
  payment_provider_key: 'Ключ эквайринга',
  payment_provider_secret: 'Секрет эквайринга',
  acquiring_phone_number: 'Номер для оплаты',

  // Query filters
  limit: 'Лимит',
  offset: 'Смещение',
  q: 'Поиск',
  user_id: 'ID пользователя',
  date_from: 'Дата от',
  date_to: 'Дата до',
};

function deriveApiPrefix() {
  const s = String(ADMIN_AUTH_PREFIX || '').trim();
  const base = s.replace(/\/admin\/auth\/?$/, '');
  return base || '/api/v1';
}

const API_PREFIX = deriveApiPrefix();

function buildUrl(path) {
  const p = String(path || '');

  if (/^https?:\/\//i.test(p)) return p;
  if (p.startsWith('/api/')) return p;
  if (p.startsWith('/')) return `${API_PREFIX}${p}`;
  return `${API_PREFIX}/${p}`;
}

async function readPayload(res) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function normalizeValidationDetails(details) {
  if (!details) return [];
  if (Array.isArray(details)) return details;
  if (Array.isArray(details?.errors)) return details.errors;
  return [];
}

function normalizeLoc(loc) {
  if (Array.isArray(loc)) {
    return loc
      .filter((x) => typeof x === 'string' || typeof x === 'number')
      .map((x) => String(x));
  }

  if (typeof loc === 'string' && loc.trim()) {
    return loc.split('.').filter(Boolean);
  }

  return [];
}

function resolveFieldName(detail) {
  const parts = normalizeLoc(detail?.loc).filter((p) => !['body', 'query', 'path', 'response'].includes(p));
  if (!parts.length) return 'Поле';

  const joined = parts.join('.');
  const last = parts[parts.length - 1];
  return FIELD_LABELS[joined] || FIELD_LABELS[last] || joined;
}

function valueToText(value) {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return '';
}

function buildValidationMessage(detail) {
  const label = resolveFieldName(detail);
  const type = String(detail?.type || '').toLowerCase();
  const ctx = detail?.ctx || {};
  const fallbackMsg = valueToText(detail?.msg);

  if (type.includes('missing')) {
    return `${label}: поле обязательно`;
  }

  if (type.includes('string_too_short')) {
    const min = valueToText(ctx.min_length);
    return `${label}: минимум ${min || '1'} симв.`;
  }

  if (type.includes('string_too_long')) {
    const max = valueToText(ctx.max_length);
    return `${label}: слишком длинное значение${max ? ` (максимум ${max} симв.)` : ''}`;
  }

  if (type.includes('list_too_short')) {
    const min = valueToText(ctx.min_length);
    return `${label}: выберите минимум ${min || '1'} элемент`;
  }

  if (type.includes('greater_than_equal')) {
    const ge = valueToText(ctx.ge);
    return `${label}: значение должно быть не меньше ${ge || 'допустимого минимума'}`;
  }

  if (type.includes('greater_than')) {
    const gt = valueToText(ctx.gt);
    return `${label}: значение должно быть больше ${gt || 'допустимого минимума'}`;
  }

  if (type.includes('less_than_equal')) {
    const le = valueToText(ctx.le);
    return `${label}: значение должно быть не больше ${le || 'допустимого максимума'}`;
  }

  if (type.includes('less_than')) {
    const lt = valueToText(ctx.lt);
    return `${label}: значение должно быть меньше ${lt || 'допустимого максимума'}`;
  }

  if (type.includes('int_parsing') || type.includes('float_parsing') || type.includes('decimal_parsing')) {
    return `${label}: введите корректное число`;
  }

  if (type.includes('datetime') || type.includes('date_parsing')) {
    return `${label}: некорректная дата/время`;
  }

  if (type.includes('bool_parsing')) {
    return `${label}: выберите корректное значение`;
  }

  if (type.includes('string_pattern_mismatch')) {
    return `${label}: неверный формат`;
  }

  if (fallbackMsg) {
    return `${label}: ${fallbackMsg}`;
  }

  return `${label}: ошибка валидации`;
}

function formatValidationDetails(details) {
  const list = normalizeValidationDetails(details);
  if (!list.length) return '';

  const unique = [];
  for (const item of list) {
    const text = buildValidationMessage(item);
    if (!text) continue;
    if (!unique.includes(text)) unique.push(text);
    if (unique.length >= 3) break;
  }

  return unique.join('; ');
}

function errorMessage(payload, status) {
  if (!payload) return `HTTP ${status}`;
  if (typeof payload === 'string') return payload;

  const details = payload?.error?.details ?? payload?.detail;
  const detailsMsg = formatValidationDetails(details);
  if (detailsMsg) return detailsMsg;

  if (payload?.error?.message) return String(payload.error.message);
  if (typeof payload?.detail === 'string') return payload.detail;
  if (payload?.detail?.error?.message) return String(payload.detail.error.message);
  if (payload?.detail?.message) return String(payload.detail.message);
  if (payload?.message) return String(payload.message);

  return `HTTP ${status}`;
}

async function ensureFreshAccessToken({ forceRefresh = false } = {}) {
  const { refreshToken } = getAdminTokens();

  if (!forceRefresh && isAccessTokenValid()) return true;
  if (!refreshToken) return false;

  try {
    await adminRefresh();
    return Boolean(getAdminTokens().accessToken);
  } catch {
    clearAdminTokens();
    return false;
  }
}

function redirectToLogin() {
  clearAdminTokens();
  try {
    navigate('/login', { replace: true });
  } catch {
    if (typeof window !== 'undefined') {
      const base = String(import.meta.env.BASE_URL || '/');
      const normalized = base.endsWith('/') ? base : `${base}/`;
      window.location.href = `${normalized}login`;
    }
  }
}

function unwrapPayload(payload) {
  if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'ok')) {
    if (payload.ok === false) {
      throw new Error(errorMessage(payload, 200));
    }
    if (Object.prototype.hasOwnProperty.call(payload, 'result')) {
      return payload.result;
    }
  }
  return payload;
}

export async function apiFetchJson(
  path,
  { method = 'GET', body, auth = true, headers: extraHeaders } = {}
) {
  const url = buildUrl(path);

  if (auth) {
    await ensureFreshAccessToken();
  }

  const headers = new Headers(extraHeaders || {});
  headers.set('Content-Type', 'application/json');

  if (auth) {
    const { accessToken } = getAdminTokens();
    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  }

  const init = {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  };

  let res = await fetch(url, init);

  if (auth && res.status === 401) {
    const ok = await ensureFreshAccessToken({ forceRefresh: true });

    if (ok) {
      const headers2 = new Headers(extraHeaders || {});
      headers2.set('Content-Type', 'application/json');
      const { accessToken } = getAdminTokens();
      if (accessToken) headers2.set('Authorization', `Bearer ${accessToken}`);

      res = await fetch(url, { ...init, headers: headers2 });
    } else {
      redirectToLogin();
    }
  }

  const payload = await readPayload(res);

  if (!res.ok) {
    if (auth && res.status === 401) {
      redirectToLogin();
    }
    throw new Error(errorMessage(payload, res.status));
  }

  return unwrapPayload(payload);
}

export default apiFetchJson;