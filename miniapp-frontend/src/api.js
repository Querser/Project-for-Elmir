// src/api.js
import { buildAuthHeaders, getTelegramInitData, setAuthToken } from "./auth";

/**
 * Можно задать в .env:
 * VITE_API_BASE_URL=http://localhost:8001
 *
 * Если пусто — используем относительные URL (удобно для одного домена).
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

/**
 * Опциональная авторизация: пробуем отправить initData в backend.
 * Если endpoint не существует — просто игнорируем (чтобы не ломать то, что работает).
 */
const AUTH_ENDPOINT_CANDIDATES = [
  "/api/v1/auth/telegram",
  "/api/v1/auth/webapp",
  "/api/v1/telegram/auth",
];

function joinUrl(path) {
  if (!API_BASE) return path;
  return API_BASE.replace(/\/$/, "") + path;
}

function unwrap(res) {
  if (!res) return res;
  if (res.ok === true && res.result != null) return res.result;
  return res;
}

/**
 * Безопасно достаём items из разных форматов ответа
 */
export function extractItems(res) {
  const u = unwrap(res);
  if (!u) return [];
  if (Array.isArray(u)) return u;
  if (Array.isArray(u.items)) return u.items;
  if (u.result && Array.isArray(u.result.items)) return u.result.items;
  return [];
}

async function parseResponse(resp) {
  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    return await resp.json();
  }
  // calendar/ics или что-то бинарное
  return await resp.blob();
}

async function apiFetch(path, options = {}) {
  const url = joinUrl(path);

  const headers = {
    Accept: "application/json",
    ...(options.headers || {}),
    ...buildAuthHeaders(),
  };

  // Если body = объект, сериализуем
  let body = options.body;
  if (
    body &&
    typeof body === "object" &&
    !(body instanceof FormData) &&
    !(body instanceof Blob)
  ) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }

  const resp = await fetch(url, {
    ...options,
    headers,
    body,
  });

  // 204
  if (resp.status === 204) return null;

  const data = await parseResponse(resp);

  if (!resp.ok) {
    let message = "Ошибка запроса";
    if (data && typeof data === "object") {
      if (data.detail) message = String(data.detail);
      if (data.error?.message) message = String(data.error.message);
      if (data.message) message = String(data.message);
    }
    const err = new Error(message);
    err.status = resp.status;
    err.data = data;
    throw err;
  }

  return data;
}

export async function apiGet(path) {
  return await apiFetch(path, { method: "GET" });
}

export async function apiPost(path, body) {
  return await apiFetch(path, { method: "POST", body });
}

export async function apiPatch(path, body) {
  return await apiFetch(path, { method: "PATCH", body });
}

export async function apiPut(path, body) {
  return await apiFetch(path, { method: "PUT", body });
}

export async function apiDelete(path) {
  return await apiFetch(path, { method: "DELETE" });
}

/**
 * Инициализация Mini App:
 * - Telegram WebApp ready/expand
 * - (опционально) отправляем initData на backend и сохраняем token, если вернулся
 */
export async function initMiniAppAuth() {
  const tg = window.Telegram?.WebApp;
  tg?.ready?.();
  tg?.expand?.();

  const { initData } = getTelegramInitData();
  if (!initData) return;

  for (const ep of AUTH_ENDPOINT_CANDIDATES) {
    try {
      const res = await apiPost(ep, { init_data: initData });
      const u = unwrap(res);
      const token = u?.token || u?.access_token || null;
      if (token) setAuthToken(token);
      return;
    } catch {
      // endpoint может не существовать — это нормально, пробуем следующий
    }
  }
}

/**
 * Получить календарь:
 * - если backend отдаёт blob (ics) — откроем его
 * - если отдаёт {url} — откроем url
 */
export async function openCalendar(trainingId) {
  const path = `/api/v1/trainings/${trainingId}/calendar`;
  const url = joinUrl(path);

  const resp = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "*/*",
      ...buildAuthHeaders(),
    },
  });

  if (!resp.ok) {
    const ct = resp.headers.get("content-type") || "";
    let msg = `Ошибка календаря (${resp.status})`;
    if (ct.includes("application/json")) {
      const j = await resp.json().catch(() => null);
      msg = j?.error?.message || j?.detail || msg;
    }
    throw new Error(msg);
  }

  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const j = await resp.json();
    const u = unwrap(j);
    const link = u?.url || u?.link;
    if (link) {
      window.open(link, "_blank", "noopener,noreferrer");
      return;
    }
    throw new Error("Backend не вернул ссылку на календарь.");
  }

  const blob = await resp.blob();
  const blobUrl = URL.createObjectURL(blob);
  window.open(blobUrl, "_blank", "noopener,noreferrer");
  setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
}
