export function lsGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

export function lsSet(key, value) {
  try { localStorage.setItem(key, value); } catch { /* ignore */ }
}

export function lsRemove(key) {
  try { localStorage.removeItem(key); } catch { /* ignore */ }
}
