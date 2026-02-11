function pad2(n) { return String(n).padStart(2, '0'); }

export function formatDateTimeLocal(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return '';
  return `${pad2(d.getDate())}.${pad2(d.getMonth() + 1)}.${d.getFullYear()} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

export function toDatetimeLocalValue(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return '';
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/**
 * Берём значение input[type=datetime-local] (YYYY-MM-DDTHH:mm)
 * и превращаем в ISO c локальным offset (+03:00 и т.п.),
 * чтобы время не "съезжало" в UTC.
 */
export function datetimeLocalToIsoWithOffset(dtLocal) {
  if (!dtLocal) return '';
  const d = new Date(dtLocal);
  if (Number.isNaN(d.getTime())) return '';

  const year = d.getFullYear();
  const month = pad2(d.getMonth() + 1);
  const day = pad2(d.getDate());
  const hh = pad2(d.getHours());
  const mm = pad2(d.getMinutes());
  const ss = '00';

  const tzMinutes = -d.getTimezoneOffset();
  const sign = tzMinutes >= 0 ? '+' : '-';
  const abs = Math.abs(tzMinutes);
  const tzh = pad2(Math.floor(abs / 60));
  const tzm = pad2(abs % 60);

  return `${year}-${month}-${day}T${hh}:${mm}:${ss}${sign}${tzh}:${tzm}`;
}

export function safeNumber(v, def = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : def;
}
