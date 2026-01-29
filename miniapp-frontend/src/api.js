// src/api.js
// Унифицированный слой API:
// - добавляет Telegram WebApp initData (prod) или dev-заголовки (dev)
// - умеет разворачивать ответы формата { ok: true, result: ... }
// - нормализует ошибки backend (detail / error / message)

import { buildAuthHeaders } from './auth';

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

async function request(path, options = {}) {
  const url = buildUrl(path);
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers || {});

  // auth headers (Telegram initData or dev headers)
  const auth = buildAuthHeaders();
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

  const res = await fetch(url, {
    method,
    headers,
    body: method === 'GET' || method === 'HEAD' ? undefined : body,
  });

  const ct = res.headers.get('content-type') || '';
  const raw = await res.text();
  const json = ct.includes('application/json') ? (tryJsonParse(raw) ?? {}) : null;

  if (!res.ok) {
    const msg = json ? normalizeErrorPayload(json) : (raw || `HTTP ${res.status}`);
    const err = new Error(msg || `HTTP ${res.status}`);
    err.status = res.status;
    err.payload = json || raw;
    throw err;
  }

  if (res.status === 204) return null;

  const data = json != null ? json : raw;
  return unwrap(data);
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
