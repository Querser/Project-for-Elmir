// src/auth.js

const LS_DEV_TELEGRAM_ID = "dev.telegram_id";
const LS_DEV_USER_ID = "dev.user_id";
const LS_AUTH_TOKEN = "auth.token";

export function getTelegramWebApp() {
  return window.Telegram?.WebApp ?? null;
}

export function isInTelegram() {
  const tg = getTelegramWebApp();
  return Boolean(tg && (tg.initData || tg.initDataUnsafe));
}

export function getTelegramUser() {
  const tg = getTelegramWebApp();
  return tg?.initDataUnsafe?.user ?? null;
}

export function getTelegramUserId() {
  const u = getTelegramUser();
  return u?.id != null ? String(u.id) : "";
}

export function getTelegramInitData() {
  const tg = getTelegramWebApp();
  const initData = tg?.initData || "";
  const initDataUnsafe = tg?.initDataUnsafe || null;
  return { initData, initDataUnsafe };
}

function lsSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

function lsGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function lsRemove(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore
  }
}

export function setDevAuth({ telegramId, userId }) {
  if (telegramId != null && String(telegramId).trim() !== "") {
    lsSet(LS_DEV_TELEGRAM_ID, String(telegramId).trim());
  } else {
    lsRemove(LS_DEV_TELEGRAM_ID);
  }

  if (userId != null && String(userId).trim() !== "") {
    lsSet(LS_DEV_USER_ID, String(userId).trim());
  } else {
    lsRemove(LS_DEV_USER_ID);
  }
}

export function getDevAuth() {
  return {
    telegramId: lsGet(LS_DEV_TELEGRAM_ID) || "",
    userId: lsGet(LS_DEV_USER_ID) || "",
  };
}

export function clearAuth() {
  lsRemove(LS_DEV_TELEGRAM_ID);
  lsRemove(LS_DEV_USER_ID);
  lsRemove(LS_AUTH_TOKEN);
}

export function setAuthToken(token) {
  if (token) lsSet(LS_AUTH_TOKEN, token);
  else lsRemove(LS_AUTH_TOKEN);
}

export function getAuthToken() {
  return lsGet(LS_AUTH_TOKEN) || "";
}

/**
 * Заголовки авторизации:
 * - В Telegram: X-Telegram-Init-Data (+ дублируем X-Telegram-Id из initDataUnsafe.user.id)
 * - В браузере (dev): X-Telegram-Id или X-User-Id из localStorage
 * - Если backend вернёт токен (опционально) — добавим Authorization
 */
export function buildAuthHeaders() {
  const headers = {};

  const { initData, initDataUnsafe } = getTelegramInitData();
  if (initData) {
    headers["X-Telegram-Init-Data"] = initData;

    // ВАЖНО: текущий бэкенд авторизует через X-Telegram-Id (core.deps.get_current_user)
    const tgId = initDataUnsafe?.user?.id;
    if (tgId) headers["X-Telegram-Id"] = String(tgId);
  } else {
    const dev = getDevAuth();
    if (dev.telegramId) headers["X-Telegram-Id"] = dev.telegramId;
    if (dev.userId) headers["X-User-Id"] = dev.userId;
  }

  const token = getAuthToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return headers;
}

/**
 * =========================
 * Совместимость со старым App.jsx
 * =========================
 * В логах сборки видно:
 *   import { initTelegramAuth, getTelegramId } from './auth'
 * Поэтому добавляем эти экспорты как алиасы, НЕ ломая текущую архитектуру.
 */

/**
 * getTelegramId():
 * - в Telegram вернёт tg user id
 * - в браузере вернёт dev telegram id (если задан)
 */
export function getTelegramId() {
  const tgId = getTelegramUserId();
  if (tgId) return tgId;

  const dev = getDevAuth();
  return dev.telegramId || "";
}

/**
 * initTelegramAuth():
 * Мягкая инициализация Telegram WebApp (ready/expand).
 * Ничего не “ломает”, даже если не в Telegram.
 */
export async function initTelegramAuth() {
  const tg = getTelegramWebApp();
  try {
    tg?.ready?.();
    tg?.expand?.();
  } catch {
    // ignore
  }

  // Возвращаем полезные данные (если App.jsx их использует — ок; если нет — тоже ок)
  const { initData, initDataUnsafe } = getTelegramInitData();
  return {
    telegramId: getTelegramId(),
    initData,
    initDataUnsafe,
    user: initDataUnsafe?.user ?? null,
  };
}
