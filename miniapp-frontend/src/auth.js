// src/auth.js

const LS_DEV_TELEGRAM_ID = "dev.telegram_id";
const LS_DEV_USER_ID = "dev.user_id";
const LS_AUTH_TOKEN = "auth.token";

export function getTelegramWebApp() {
  return window.Telegram?.WebApp ?? null;
}

export function getTelegramInitData() {
  const tg = getTelegramWebApp();
  const initData = tg?.initData || "";
  const initDataUnsafe = tg?.initDataUnsafe || null;
  return { initData, initDataUnsafe };
}

export function setDevAuth({ telegramId, userId }) {
  if (telegramId != null && String(telegramId).trim() !== "") {
    localStorage.setItem(LS_DEV_TELEGRAM_ID, String(telegramId).trim());
  } else {
    localStorage.removeItem(LS_DEV_TELEGRAM_ID);
  }

  if (userId != null && String(userId).trim() !== "") {
    localStorage.setItem(LS_DEV_USER_ID, String(userId).trim());
  } else {
    localStorage.removeItem(LS_DEV_USER_ID);
  }
}

export function getDevAuth() {
  return {
    telegramId: localStorage.getItem(LS_DEV_TELEGRAM_ID) || "",
    userId: localStorage.getItem(LS_DEV_USER_ID) || "",
  };
}

export function clearAuth() {
  localStorage.removeItem(LS_DEV_TELEGRAM_ID);
  localStorage.removeItem(LS_DEV_USER_ID);
  localStorage.removeItem(LS_AUTH_TOKEN);
}

export function setAuthToken(token) {
  if (token) localStorage.setItem(LS_AUTH_TOKEN, token);
  else localStorage.removeItem(LS_AUTH_TOKEN);
}

export function getAuthToken() {
  return localStorage.getItem(LS_AUTH_TOKEN) || "";
}

/**
 * Заголовки авторизации:
 * - В Telegram: X-Telegram-Init-Data
 * - В браузере (dev): X-Telegram-Id или X-User-Id
 * - Если backend вернёт токен (опционально) — добавим Authorization
 */
export function buildAuthHeaders() {
  const headers = {};

  const { initData, initDataUnsafe } = getTelegramInitData();
  if (initData) {
    headers["X-Telegram-Init-Data"] = initData;

    // Иногда бэкенды любят отдельный хедер с telegram_id
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
