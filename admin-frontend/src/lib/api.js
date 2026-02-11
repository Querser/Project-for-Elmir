import { ADMIN_AUTH_PREFIX } from '../config.js';
import {
  getAdminTokens,
  isAccessTokenValid,
  adminRefresh,
  clearAdminTokens,
} from './adminAuth.js';
import { navigate } from './router.js';

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

function errorMessage(payload, status) {
  if (!payload) return `HTTP ${status}`;
  if (typeof payload === 'string') return payload;
  if (payload?.error?.message) return String(payload.error.message);

  const details = payload?.error?.details || payload?.detail;
  if (Array.isArray(details) && details.length) {
    const first = details[0];
    const loc = Array.isArray(first?.loc) ? first.loc.join('.') : '';
    const msg = first?.msg ? String(first.msg) : '';
    if (loc && msg) return `${loc}: ${msg}`;
    if (msg) return msg;
  }

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
