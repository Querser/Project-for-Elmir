// src/api.js
// Унифицированный слой API:
// - добавляет Telegram WebApp initData (prod) или dev-заголовки (dev)
// - умеет разворачивать ответы формата { ok: true, result: ... }
// - нормализует ошибки backend (detail / error / message)
// - НЕ показывает HTML 502/503 от nginx пользователю
// - Делает retry для GET/HEAD при временных ошибках (502/503/504) и сетевых проблемах

import { buildAuthHeaders, waitForTelegramInitData } from './auth';

// По умолчанию работаем от того же origin, что и миниапп (nginx проксирует /api/ -> backend)
// Можно переопределить через VITE_API_BASE (например, при локальной разработке без nginx).
export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').toString().trim();

function buildUrl(path) {
  if (!path) return API_BASE || '';
  if (/^https?:\/\//i.test(path)) return path;

  const base = (API_BASE || '').replace(/\/+$/, '');
  const p = path.replace(/^\/+/, '');
  if (!base) return `/${p}`;
  return `${base}/${p}`;
}

function tryJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function looksLikeJson(text) {
  if (!text) return false;
  const t = text.trim();
  return (t.startsWith('{') && t.endsWith('}')) || (t.startsWith('[') && t.endsWith(']'));
}

function normalizeErrorPayload(payload) {
  if (!payload) return 'Неизвестная ошибка';

  // FastAPI: { detail: '...' } или { detail: { error: { message } } }
  if (typeof payload.detail === 'string') return payload.detail;
  if (payload.detail && typeof payload.detail === 'object') {
    const d = payload.detail;
    if (typeof d.message === 'string') return d.message;
    if (d.error && typeof d.error.message === 'string') return d.error.message;
    if (Array.isArray(d)) return 'Ошибка валидации данных';
  }

  // Кастомный формат: { error: { message } }
  if (payload.error && typeof payload.error.message === 'string') return payload.error.message;

  if (typeof payload.message === 'string') return payload.message;

  return 'Неизвестная ошибка';
}

/**
 * Разворачивает success_response:
 *   { ok: true, result: ... } -> ...
 */
export function unwrap(res) {
  if (!res) return res;
  if (res.ok === true && Object.prototype.hasOwnProperty.call(res, 'result')) return res.result;
  return res;
}

/**
 * Универсально достаёт items для списков.
 */
export function extractItems(res) {
  const data = unwrap(res);
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.results)) return data.results;
  return [];
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isTransientStatus(status) {
  return status === 502 || status === 503 || status === 504;
}

function isLikelyHtml(contentType, raw) {
  if ((contentType || '').includes('text/html')) return true;
  const t = (raw || '').trim();
  return t.startsWith('<!DOCTYPE html') || t.startsWith('<html') || t.includes('<title>502') || t.includes('Bad Gateway');
}

function makeFriendlyErrorMessage({ status, contentType, json, raw }) {
  // Если JSON-ошибка — показываем нормализованную
  if (json) return normalizeErrorPayload(json) || `HTTP ${status}`;

  // Если это HTML от nginx (502/503) — не показываем HTML-портянку
  if (isLikelyHtml(contentType, raw)) {
    if (status === 502 || status === 503) {
      return 'Сервис временно недоступен. Обнови страницу через пару секунд.';
    }
    return `HTTP ${status}`;
  }

  // Если plain text (короткий) — можно показать
  const txt = (raw || '').trim();
  if (txt && txt.length <= 200 && !/[<>]/.test(txt)) return txt;

  return `HTTP ${status}`;
}

async function request(path, options = {}) {
  const url = buildUrl(path);
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers || {});

  // auth headers (Telegram initData or dev headers)
  let auth = buildAuthHeaders();
  const inTelegramWebView = typeof window !== 'undefined' && Boolean(window.Telegram?.WebApp);
  if (!auth['X-Telegram-Init-Data'] && inTelegramWebView) {
    await waitForTelegramInitData(1200, 50);
    auth = buildAuthHeaders();
  }
  Object.entries(auth || {}).forEach(([k, v]) => {
    if (v == null || v === '') return;
    if (!headers.has(k)) headers.set(k, String(v));
  });

  let body = options.body;
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
  const isBlob = typeof Blob !== 'undefined' && body instanceof Blob;

  // Если body — объект, отправляем как JSON
  if (body != null && typeof body === 'object' && !isFormData && !isBlob && !(body instanceof ArrayBuffer)) {
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    body = JSON.stringify(body);
  }

  // Retry только для безопасных запросов
  const maxAttempts = (method === 'GET' || method === 'HEAD') ? 5 : 1;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const res = await fetch(url, {
        method,
        headers,
        body: method === 'GET' || method === 'HEAD' ? undefined : body,
      });

      const ct = res.headers.get('content-type') || '';
      const raw = await res.text();

      // Иногда JSON приходит без корректного content-type
      const maybeJson = ct.includes('application/json') || looksLikeJson(raw);
      const json = maybeJson ? (tryJsonParse(raw) ?? null) : null;

      if (!res.ok) {
        const msg = makeFriendlyErrorMessage({ status: res.status, contentType: ct, json, raw });

        const err = new Error(msg || `HTTP ${res.status}`);
        err.status = res.status;
        err.payload = json || raw;
        err.isTransient = isTransientStatus(res.status);
        throw err;
      }

      if (res.status === 204) return null;

      return unwrap(json != null ? json : raw);
    } catch (e) {
      const isNetworkError =
        e instanceof TypeError ||
        (typeof e?.message === 'string' && /failed to fetch|networkerror/i.test(e.message));

      const canRetry = attempt < maxAttempts && (e?.isTransient === true || isNetworkError);

      if (canRetry) {
        // экспоненциальная задержка + небольшой джиттер
        const backoff = 250 * (2 ** (attempt - 1));
        const jitter = Math.floor(Math.random() * 120);
        await sleep(backoff + jitter);
        continue;
      }

      throw e;
    }
  }

  throw new Error('Неизвестная ошибка');
}

// === Public API ===

export async function apiFetch(path, options = {}) {
  return request(path, options);
}

export function apiGet(path, headers) {
  return request(path, { method: 'GET', headers });
}

export function apiPost(path, body, headers) {
  return request(path, { method: 'POST', body, headers });
}

export function apiPatch(path, body, headers) {
  return request(path, { method: 'PATCH', body, headers });
}

export function apiDelete(path, headers) {
  return request(path, { method: 'DELETE', headers });
}
