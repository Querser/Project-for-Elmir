import { ADMIN_AUTH_PREFIX } from '../config.js';
import { lsGet, lsSet, lsRemove } from './storage.js';

const LS_ACCESS = 'admin.access_token';
const LS_REFRESH = 'admin.refresh_token';
const LS_EXPIRES_AT = 'admin.expires_at_ms';

function nowMs() {
  return Date.now();
}

function parseJwtExpMs(token) {
  try {
    const parts = String(token || '').split('.');
    if (parts.length < 2) return 0;
    const payloadRaw = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(payloadRaw);
    const exp = Number(payload?.exp || 0);
    if (!Number.isFinite(exp) || exp <= 0) return 0;
    return exp * 1000;
  } catch {
    return 0;
  }
}

export function getAdminTokens() {
  const accessToken = lsGet(LS_ACCESS) || '';
  const refreshToken = lsGet(LS_REFRESH) || '';
  const expiresAtMs = Number(lsGet(LS_EXPIRES_AT) || '0') || 0;
  return { accessToken, refreshToken, expiresAtMs };
}

export function setAdminTokens({ accessToken, refreshToken, expiresInSeconds }) {
  if (accessToken) lsSet(LS_ACCESS, String(accessToken));
  else lsRemove(LS_ACCESS);

  if (refreshToken) lsSet(LS_REFRESH, String(refreshToken));
  else lsRemove(LS_REFRESH);

  let expMs = 0;
  if (expiresInSeconds != null && expiresInSeconds !== '') {
    const sec = Number(expiresInSeconds);
    if (Number.isFinite(sec) && sec > 0) {
      expMs = nowMs() + sec * 1000;
    }
  }
  if (!expMs && accessToken) {
    expMs = parseJwtExpMs(accessToken);
  }
  if (expMs > 0) lsSet(LS_EXPIRES_AT, String(expMs));
  else lsRemove(LS_EXPIRES_AT);
}

export function clearAdminTokens() {
  lsRemove(LS_ACCESS);
  lsRemove(LS_REFRESH);
  lsRemove(LS_EXPIRES_AT);
}

export function isAccessTokenValid(skewSeconds = 30) {
  const { accessToken, expiresAtMs } = getAdminTokens();
  if (!accessToken) return false;
  const expMs = expiresAtMs || parseJwtExpMs(accessToken);
  if (!expMs) return false;
  return expMs > nowMs() + skewSeconds * 1000;
}

export function isAuthenticated() {
  const { accessToken, refreshToken } = getAdminTokens();
  return Boolean(accessToken || refreshToken);
}

let ensureInFlight = null;

export async function ensureSession() {
  if (isAccessTokenValid()) return true;

  const { refreshToken } = getAdminTokens();
  if (!refreshToken) return false;

  if (ensureInFlight) return ensureInFlight;

  ensureInFlight = (async () => {
    try {
      await adminRefresh();
      return isAccessTokenValid() || Boolean(getAdminTokens().accessToken);
    } catch {
      clearAdminTokens();
      return false;
    } finally {
      ensureInFlight = null;
    }
  })();

  return ensureInFlight;
}

export function adminLogout() {
  clearAdminTokens();
}

export function getAdminAccessToken() {
  return getAdminTokens().accessToken;
}

export function getAdminRefreshToken() {
  return getAdminTokens().refreshToken;
}

function buildUrl(path) {
  if (/^https?:\/\//i.test(path)) return path;
  return path;
}

function normalizeErrorPayload(payload) {
  if (!payload) return '';
  if (typeof payload === 'string') return payload;

  if (typeof payload.detail === 'string') return payload.detail;
  if (payload.detail && typeof payload.detail === 'object') {
    const details = payload.detail;
    if (details.error && typeof details.error.message === 'string') return details.error.message;
    if (typeof details.message === 'string') return details.message;
  }

  if (payload.error && typeof payload.error.message === 'string') return payload.error.message;
  if (typeof payload.message === 'string') return payload.message;

  return '';
}

async function rawJsonRequest(url, { method = 'POST', body } = {}) {
  const res = await fetch(buildUrl(url), {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body != null ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }

  if (!res.ok) {
    const msg = normalizeErrorPayload(json) || `HTTP ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    err.payload = json || text;
    throw err;
  }

  return json;
}

function pickTokenResponse(data) {
  const payload =
    data && typeof data === 'object' && data.result && typeof data.result === 'object'
      ? data.result
      : data;

  const access =
    payload?.access_token || payload?.accessToken || payload?.token || payload?.access || '';
  const refresh =
    payload?.refresh_token || payload?.refreshToken || payload?.refresh || '';
  const expiresIn =
    payload?.access_expires_in ??
    payload?.expires_in ??
    payload?.expiresIn ??
    payload?.expires ??
    null;
  return { accessToken: access, refreshToken: refresh, expiresInSeconds: expiresIn };
}

export async function adminLogin(username, password) {
  const data = await rawJsonRequest(`${ADMIN_AUTH_PREFIX}/login`, {
    method: 'POST',
    body: { username, password },
  });

  const tokens = pickTokenResponse(data);
  if (!tokens.accessToken) throw new Error('Backend did not return access token');

  setAdminTokens(tokens);
  return tokens;
}

let refreshInFlight = null;

export async function adminRefresh() {
  const { refreshToken } = getAdminTokens();
  if (!refreshToken) throw new Error('No refresh token');

  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    try {
      const data = await rawJsonRequest(`${ADMIN_AUTH_PREFIX}/refresh`, {
        method: 'POST',
        body: { refresh_token: refreshToken },
      });

      const tokens = pickTokenResponse(data);
      if (!tokens.accessToken) throw new Error('Backend did not return access token on refresh');

      setAdminTokens({
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken || refreshToken,
        expiresInSeconds: tokens.expiresInSeconds,
      });

      return tokens;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}
