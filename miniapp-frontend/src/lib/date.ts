export function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

export function toISODate(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

export function getMonday(d: Date): Date {
  const date = new Date(d);
  const day = (date.getDay() + 6) % 7; // Mon=0
  date.setDate(date.getDate() - day);
  date.setHours(0, 0, 0, 0);
  return date;
}

export function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function ruWeekdayShort(d: Date): string {
  const map = ["ВС", "ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ"];
  return map[d.getDay()];
}

export function formatHomeHeading(date: Date, city?: string): string {
  const fmt = new Intl.DateTimeFormat("ru-RU", { weekday: "long", day: "numeric", month: "long" });
  const txt = fmt.format(date);
  const cap = txt.charAt(0).toUpperCase() + txt.slice(1);
  return city ? `${cap} · ${city}` : cap;
}

export function safeText(v: any, fallback = "—"): string {
  const s = (v ?? "").toString().trim();
  return s ? s : fallback;
}

export function formatTimeHHMM(dateStr?: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return "—";
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

export function addMinutes(dateStr: string, minutes: number): Date | null {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return null;
  d.setMinutes(d.getMinutes() + minutes);
  return d;
}
