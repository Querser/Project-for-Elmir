import { getTelegramInitData } from "./telegram";

export type ApiFetchOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  headers?: Record<string, string>;
  body?: any;
  token?: string;
};

export const API_ENDPOINTS = {
  authTelegram: "/api/v1/auth/telegram",
  trainings: "/api/v1/trainings",
  rating: "/api/v1/rating",
  profile: "/api/v1/profile",
  notifications: "/api/v1/notifications",
  contacts: "/api/v1/contacts",
  // опционально (если у тебя есть) — список локаций
  locations: "/api/v1/locations",
};

export async function apiFetch<T = any>(path: string, opts: ApiFetchOptions = {}): Promise<T> {
  const method = opts.method || "GET";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers || {}),
  };

  if (opts.token) headers["Authorization"] = `Bearer ${opts.token}`;

  const tgInitData = getTelegramInitData();
  if (tgInitData) headers["X-Telegram-Init-Data"] = tgInitData;

  const res = await fetch(path, {
    method,
    headers,
    body: opts.body != null ? JSON.stringify(opts.body) : undefined,
  });

  const raw = await res.text();
  let data: any = null;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {
    data = raw;
  }

  if (!res.ok) {
    const msg =
      (data && (data.message || data.error || data.detail)) ? (data.message || data.error || data.detail)
      : `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data as T;
}

/**
 * Этап 12.1: попытка получить access_token через /auth/telegram.
 * Если у тебя на бэке авторизация идёт только по X-Telegram-Init-Data — это тоже ок.
 */
export async function tryTelegramAuth(): Promise<string> {
  const tgInitData = getTelegramInitData();
  if (!tgInitData) return "";

  try {
    const data: any = await apiFetch(API_ENDPOINTS.authTelegram, {
      method: "POST",
      body: { init_data: tgInitData },
    });

    const token =
      data?.access_token ||
      data?.token ||
      data?.result?.access_token ||
      data?.data?.access_token ||
      "";

    return token || "";
  } catch {
    return "";
  }
}
