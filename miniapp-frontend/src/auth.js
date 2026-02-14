// src/auth.js

const LS_DEV_TELEGRAM_ID = "dev.telegram_id";
const LS_DEV_USER_ID = "dev.user_id";
const LS_AUTH_TOKEN = "auth.token";

export function getTelegramWebApp() {
  return window.Telegram?.WebApp ?? null;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function readParam(raw, name) {
  const source = String(raw || "").trim();
  if (!source) return "";

  const withoutPrefix = source.startsWith("?") || source.startsWith("#")
    ? source.slice(1)
    : source;

  const queryPart = withoutPrefix.includes("?")
    ? withoutPrefix.slice(withoutPrefix.indexOf("?") + 1)
    : withoutPrefix;

  try {
    const params = new URLSearchParams(queryPart);
    return params.get(name) || "";
  } catch {
    return "";
  }
}

function getInitDataFromLocation() {
  if (typeof window === "undefined") return "";
  const fromSearch = readParam(window.location?.search, "tgWebAppData");
  if (fromSearch) return fromSearch;
  return readParam(window.location?.hash, "tgWebAppData");
}

function getTelegramIdFromLocation() {
  if (typeof window === "undefined") return "";
  const fromSearch = readParam(window.location?.search, "tg_id") || readParam(window.location?.search, "telegram_id");
  if (fromSearch) return String(fromSearch).trim();
  const fromHash = readParam(window.location?.hash, "tg_id") || readParam(window.location?.hash, "telegram_id");
  return String(fromHash || "").trim();
}

function normalizeTelegramId(value) {
  const s = String(value ?? "").trim();
  if (!s) return "";
  return /^-?\d+$/.test(s) ? s : "";
}

function parseUserFromInitData(initData) {
  const raw = String(initData || "").trim();
  if (!raw) return null;
  try {
    const params = new URLSearchParams(raw);
    const userRaw = params.get("user");
    if (!userRaw) return null;
    const parsed = JSON.parse(userRaw);
    if (!parsed || parsed.id == null) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function isInTelegram() {
  const tg = getTelegramWebApp();
  return Boolean(
    (tg && (tg.initData || tg.initDataUnsafe)) ||
      getInitDataFromLocation(),
  );
}

export function getTelegramUser() {
  const tg = getTelegramWebApp();
  const fromSdk = tg?.initDataUnsafe?.user ?? null;
  if (fromSdk && fromSdk.id != null) return fromSdk;
  const parsed = parseUserFromInitData(getTelegramInitData().initData);
  if (parsed && parsed.id != null) return parsed;
  const fromLocation = normalizeTelegramId(getTelegramIdFromLocation());
  if (fromLocation) return { id: Number(fromLocation) };
  return null;
}

export function getTelegramUserId() {
  const u = getTelegramUser();
  return u?.id != null ? String(u.id) : "";
}

export function getTelegramInitData() {
  const tg = getTelegramWebApp();
  const initData = String(tg?.initData || getInitDataFromLocation() || "");
  const initDataUnsafe = tg?.initDataUnsafe || null;
  return { initData, initDataUnsafe };
}

export async function waitForTelegramIdentity(timeoutMs = 5000, stepMs = 100) {
  const timeout = Number(timeoutMs) > 0 ? Number(timeoutMs) : 0;
  const step = Number(stepMs) > 0 ? Number(stepMs) : 100;

  let { initData } = getTelegramInitData();
  let telegramId = getTelegramUserId();
  if (initData || telegramId) return { initData, telegramId };

  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const tg = getTelegramWebApp();
    try {
      tg?.ready?.();
    } catch {
      // ignore
    }
    await sleep(step);
    ({ initData } = getTelegramInitData());
    telegramId = getTelegramUserId();
    if (initData || telegramId) return { initData, telegramId };
  }

  ({ initData } = getTelegramInitData());
  telegramId = getTelegramUserId();
  return { initData, telegramId };
}

export async function waitForTelegramInitData(timeoutMs = 5000, stepMs = 100) {
  const identity = await waitForTelegramIdentity(timeoutMs, stepMs);
  return identity.initData;
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
  const parsedUser = parseUserFromInitData(initData);
  const locationTgId = normalizeTelegramId(getTelegramIdFromLocation());
  const tgId = initDataUnsafe?.user?.id ?? parsedUser?.id ?? locationTgId ?? null;

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
  const parsedUser = parseUserFromInitData(initData);
  return {
    telegramId: getTelegramId(),
    initData,
    initDataUnsafe,
    user: initDataUnsafe?.user ?? parsedUser ?? null,
  };
}
