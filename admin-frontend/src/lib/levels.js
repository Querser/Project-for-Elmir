export const CANONICAL_LEVEL_NAMES = ['Новичок', 'Средний-', 'Средний', 'Средний+'];

function normalizeRaw(value) {
  if (value == null) return '';
  return String(value).trim().replace('−', '-');
}

export function normalizeLevelName(value) {
  const raw = normalizeRaw(value);
  if (!raw) return '';
  const lower = raw.toLowerCase();

  if (lower.includes('нович')) return 'Новичок';
  if (lower.includes('средний-')) return 'Средний-';
  if (lower === 'средний') return 'Средний';
  if (lower.includes('средний+')) return 'Средний+';

  return '';
}

export function filterCanonicalLevels(levels) {
  if (!Array.isArray(levels)) return [];

  const normalized = levels
    .map((item) => {
      const canonical = normalizeLevelName(item?.name ?? item?.title ?? item?.level);
      if (!canonical) return null;
      return {
        ...item,
        name: canonical,
      };
    })
    .filter(Boolean);

  const byName = new Map();
  for (const lvl of normalized) {
    if (!byName.has(lvl.name)) byName.set(lvl.name, lvl);
  }

  return CANONICAL_LEVEL_NAMES
    .map((name) => byName.get(name))
    .filter(Boolean);
}
