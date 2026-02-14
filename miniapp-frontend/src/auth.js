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
 * Auth headers:
 * - Telegram: X-Telegram-Init-Data + X-Telegram-Id
 * - Browser DEV: X-Telegram-Id / X-User-Id from localStorage
 * - Optional bearer token from localStorage
 */
export function buildAuthHeaders() {
  const headers = {};

  const { initData, initDataUnsafe } = getTelegramInitData();
  const tgId = initDataUnsafe?.user?.id;

  if (initData) {
    headers["X-Telegram-Init-Data"] = initData;
  }

  if (tgId != null && tgId !== "") {
    headers["X-Telegram-Id"] = String(tgId);
  }

  // Use DEV auth only when Telegram identity is absent.
  if (!initData && (tgId == null || tgId === "")) {
    const dev = getDevAuth();
    if (dev.telegramId) headers["X-Telegram-Id"] = dev.telegramId;
    if (dev.userId) headers["X-User-Id"] = dev.userId;
  }

  const token = getAuthToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return headers;
}

export function getTelegramId() {
  const tgId = getTelegramUserId();
  if (tgId) return tgId;

  const dev = getDevAuth();
  return dev.telegramId || "";
}

export async function initTelegramAuth() {
  const tg = getTelegramWebApp();
  try {
    tg?.ready?.();
    tg?.expand?.();
  } catch {
    // ignore
  }

  const { initData, initDataUnsafe } = getTelegramInitData();
  return {
    telegramId: getTelegramId(),
    initData,
    initDataUnsafe,
    user: initDataUnsafe?.user ?? null,
  };
}