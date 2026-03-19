import { API_BASE } from '../api';

function normalizeText(value) {
  if (value == null) return '';
  return String(value).trim();
}

function detectApiOrigin() {
  const base = normalizeText(API_BASE);
  if (!base) return '';
  const fallbackOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
  try {
    const parsed = new URL(base, fallbackOrigin);
    return parsed.origin;
  } catch {
    return '';
  }
}

export function resolveMediaUrl(raw) {
  const value = normalizeText(raw);
  if (!value) return '';

  if (/^(data:|blob:)/i.test(value)) return value;
  if (/^https?:\/\//i.test(value)) return value;
  if (/^\/\//.test(value)) {
    const protocol = typeof window !== 'undefined' ? window.location?.protocol || 'https:' : 'https:';
    return `${protocol}${value}`;
  }

  const apiOrigin = detectApiOrigin();
  if (value.startsWith('/')) {
    if (apiOrigin) return `${apiOrigin}${value}`;
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
      return new URL(value, origin).toString();
    } catch {
      return value;
    }
  }

  try {
    if (apiOrigin) return new URL(value, `${apiOrigin}/`).toString();
    const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
    return new URL(value, `${origin}/`).toString();
  } catch {
    return value;
  }
}
