import { useEffect, useState } from 'react';

const NAV_EVENT = 'app:navigate';
const RAW_BASE = String(import.meta.env.BASE_URL || '/');

function normalizePathname(input) {
  let p = input || '/';

  try {
    if (p.startsWith('http://') || p.startsWith('https://')) {
      p = new URL(p).pathname;
    }
  } catch {
    // noop
  }

  if (p.includes('#')) p = p.split('#')[0] || '/';
  if (p.includes('?')) p = p.split('?')[0] || '/';

  try {
    p = decodeURIComponent(p);
  } catch {
    // noop
  }

  if (!p.startsWith('/')) p = '/' + p;
  p = p.replace(/\/{2,}/g, '/');
  if (p.length > 1 && p.endsWith('/')) p = p.slice(0, -1);
  return p || '/';
}

function normalizeBasePath(base) {
  const b = normalizePathname(base || '/');
  if (b === '/') return '/';
  return b.endsWith('/') ? b : `${b}/`;
}

const BASE_PATH = normalizeBasePath(RAW_BASE);

function stripBase(pathname) {
  const p = normalizePathname(pathname);
  if (BASE_PATH === '/') return p;

  const baseNoSlash = BASE_PATH.slice(0, -1);
  if (p === baseNoSlash) return '/';
  if (p.startsWith(BASE_PATH)) {
    const next = `/${p.slice(BASE_PATH.length)}`;
    return normalizePathname(next);
  }
  return p;
}

function withBase(pathname) {
  const p = normalizePathname(pathname);
  if (BASE_PATH === '/') return p;
  if (p === '/') return BASE_PATH.slice(0, -1);
  return `${BASE_PATH.slice(0, -1)}${p}`;
}

function getLocation() {
  return {
    pathname: stripBase(window.location.pathname),
    search: window.location.search || '',
    hash: window.location.hash || '',
    state: window.history.state ?? null,
  };
}

function notify() {
  window.dispatchEvent(new Event(NAV_EVENT));
}

export function navigate(to, opts = {}) {
  const { replace = false, state = null } = opts;

  let url = '/';
  if (typeof to === 'string') url = to;
  else if (to && typeof to === 'object' && typeof to.pathname === 'string') url = to.pathname;

  const target = withBase(url);
  if (replace) window.history.replaceState(state, '', target);
  else window.history.pushState(state, '', target);
  notify();
}

export function useLocation() {
  const [loc, setLoc] = useState(() => getLocation());

  useEffect(() => {
    const onPopState = () => setLoc(getLocation());
    const onNavigate = () => setLoc(getLocation());

    window.addEventListener('popstate', onPopState);
    window.addEventListener(NAV_EVENT, onNavigate);
    return () => {
      window.removeEventListener('popstate', onPopState);
      window.removeEventListener(NAV_EVENT, onNavigate);
    };
  }, []);

  return loc;
}

export function matchRoute(pathname, pattern) {
  const p = normalizePathname(pathname);
  const pat = normalizePathname(pattern);

  if (pat === '/' && p === '/') return { pattern, params: {}, pathname: p };

  const a = p.split('/').filter(Boolean);
  const b = pat.split('/').filter(Boolean);
  if (a.length !== b.length) return null;

  const params = {};
  for (let i = 0; i < b.length; i += 1) {
    const ps = b[i];
    const as = a[i];
    if (ps.startsWith(':')) {
      params[ps.slice(1)] = as;
      continue;
    }
    if (ps !== as) return null;
  }

  return { pattern, params, pathname: p };
}

