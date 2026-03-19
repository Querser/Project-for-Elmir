import { useEffect, useMemo, useRef, useState } from 'react';
import { apiFetch } from '../api';
import { resolveMediaUrl as resolveAssetUrl } from '../utils/media';

/**
 * РРЅРѕРіРґР° Р±РµРє РѕС‚РґР°РµС‚ UTF-8 Р±Р°Р№С‚С‹, РЅРѕ РѕРЅРё СѓР¶Рµ РїСЂРµРІСЂР°С‰РµРЅС‹ РІ СЃС‚СЂРѕРєСѓ РєР°Рє Latin-1,
 * РїРѕСЌС‚РѕРјСѓ РІ JS РїСЂРёС…РѕРґРёС‚ "ГђВўГђВµГ‘..." РІРјРµСЃС‚Рѕ "РўСЂРµ...".
 * Р­С‚Р° С„СѓРЅРєС†РёСЏ РїС‹С‚Р°РµС‚СЃСЏ РІРѕСЃСЃС‚Р°РЅРѕРІРёС‚СЊ РЅРѕСЂРјР°Р»СЊРЅС‹Р№ UTF-8.
 */
function maybeFixUtf8Mojibake(value) {
  if (value == null) return '';
  const s = typeof value === 'string' || typeof value === 'number' ? String(value) : '';
  if (!s) return '';
  // СЌРІСЂРёСЃС‚РёРєР°: С‚РёРїРёС‡РЅС‹Рµ СЃРёРјРІРѕР»С‹ РєСЂР°РєРѕР·СЏР±СЂ
  if (!/[ГђГ‘]/.test(s)) return s;

  try {
    const bytes = new Uint8Array([...s].map((ch) => ch.charCodeAt(0)));
    const decoded = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
    // РµСЃР»Рё РїРѕСЃР»Рµ РґРµРєРѕРґР° РїРѕСЏРІРёР»Р°СЃСЊ РєРёСЂРёР»Р»РёС†Р° вЂ” Р·РЅР°С‡РёС‚ СЃС‚Р°Р»Рѕ Р»СѓС‡С€Рµ
    if (/[\u0400-\u04FF]/.test(decoded)) return decoded;
    return s;
  } catch {
    return s;
  }
}

function parseDate(value) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatTime(dt) {
  if (!dt) return '';
  return dt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(dt) {
  if (!dt) return '';
  return dt.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'long' });
}

function toNumber(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function normalizeLocationLabel(loc) {
  if (loc == null) return '';
  if (typeof loc === 'string' || typeof loc === 'number') return maybeFixUtf8Mojibake(loc).trim();

  const raw =
    loc?.name ??
    loc?.title ??
    loc?.label ??
    loc?.full_address ??
    loc?.fullAddress ??
    loc?.address ??
    loc?.address_text ??
    loc?.addressText ??
    '';

  return maybeFixUtf8Mojibake(raw).toString().trim();
}

function pickFirstNonEmptyString(values) {
  for (const v of values) {
    if (v == null) continue;
    const s = typeof v === 'string' || typeof v === 'number' ? maybeFixUtf8Mojibake(v).trim() : normalizeLocationLabel(v);
    if (s) return s;
  }
  return '';
}

function parseTierPeople(title) {
  if (!title) return null;
  const t = maybeFixUtf8Mojibake(title);
  const m = String(t).match(/(\d{1,2})/);
  if (!m) return null;
  const n = Number(m[1]);
  return Number.isFinite(n) ? n : null;
}

function buildLevelChips(t) {
  const minLv = maybeFixUtf8Mojibake(t?.min_level_name ?? '').toString().trim();
  const maxLv = maybeFixUtf8Mojibake(t?.max_level_name ?? '').toString().trim();
  return [minLv, maxLv].filter(Boolean);
}

function sameId(a, b) {
  if (a == null || b == null) return false;
  const na = Number(a);
  const nb = Number(b);
  if (Number.isFinite(na) && Number.isFinite(nb)) return na === nb;
  return String(a) === String(b);
}

function extractLatLon(obj) {
  if (!obj) return { lat: null, lon: null };

  const latCandidates = [
    obj.lat,
    obj.latitude,
    obj.geo_lat,
    obj.geoLat,
    obj.location_lat,
    obj.locationLat,
    obj.coords?.lat,
    obj.coords?.latitude,
  ];

  const lonCandidates = [
    obj.lon,
    obj.lng,
    obj.longitude,
    obj.geo_lon,
    obj.geoLon,
    obj.location_lon,
    obj.locationLon,
    obj.coords?.lon,
    obj.coords?.lng,
    obj.coords?.longitude,
  ];

  const lat = latCandidates.map(toNumber).find((x) => x != null) ?? null;
  const lon = lonCandidates.map(toNumber).find((x) => x != null) ?? null;

  return { lat, lon };
}

function participantDisplayName(item) {
  const fullName = maybeFixUtf8Mojibake(item?.full_name ?? '').toString().trim();
  if (fullName) return fullName;

  const first = maybeFixUtf8Mojibake(item?.first_name ?? '').toString().trim();
  const last = maybeFixUtf8Mojibake(item?.last_name ?? '').toString().trim();
  const joined = [first, last].filter(Boolean).join(' ').trim();
  if (joined) return joined;

  const rawUsername = maybeFixUtf8Mojibake(item?.username ?? '').toString().trim();
  if (rawUsername) return rawUsername.startsWith('@') ? rawUsername : `@${rawUsername}`;

  if (item?.user_id != null) return `Игрок #${item.user_id}`;
  return 'Игрок';
}

function participantMeta(item, { isAmpLua = false } = {}) {
  const parts = [];
  const rawUsername = maybeFixUtf8Mojibake(item?.username ?? '').toString().trim();
  if (rawUsername) {
    parts.push(rawUsername.startsWith('@') ? rawUsername : `@${rawUsername}`);
  }

  const levelName = maybeFixUtf8Mojibake(item?.level_name ?? '').toString().trim();
  if (levelName) parts.push(levelName);

  if (isAmpLua) {
    const positionLabel = positionDisplayLabelFromKey(
      item?.position_key ?? item?.positionKey ?? '',
      item?.position_label ?? item?.positionLabel ?? item?.position_name ?? item?.positionName ?? '',
      item?.team ?? item?.team_name ?? item?.teamName ?? item?.team_id ?? item?.teamId ?? '',
    );
    if (positionLabel) parts.push(`Позиция: ${positionLabel}`);
  }

  return parts.join(' • ');
}

function participantAvatarLetter(item) {
  const name = participantDisplayName(item).replace(/^@/, '').trim();
  return name ? name[0].toUpperCase() : '•';
}

function resolveMediaUrl(raw) {
  const value = maybeFixUtf8Mojibake(raw ?? '').toString().trim();
  if (!value) return '';
  return resolveAssetUrl(value);
}

function isVideoKind(value) {
  const normalized = maybeFixUtf8Mojibake(value ?? '').toString().trim().toLowerCase();
  if (!normalized) return false;
  return normalized.includes('video') || normalized.includes('mp4') || normalized.includes('webm') || normalized.includes('mov');
}

function inferMediaKind(url, candidate) {
  if (isVideoKind(candidate?.type) || isVideoKind(candidate?.kind) || isVideoKind(candidate?.media_type) || isVideoKind(candidate?.mime) || isVideoKind(candidate?.content_type)) {
    return 'video';
  }
  if (/\.(mp4|webm|mov|m4v)(\?|#|$)/i.test(url)) {
    return 'video';
  }
  return 'image';
}

function extractMediaUrl(entry) {
  if (entry == null) return '';

  if (typeof entry === 'string' || typeof entry === 'number') {
    return resolveMediaUrl(entry);
  }

  if (typeof entry !== 'object') return '';

  const raw =
    entry?.url ??
    entry?.src ??
    entry?.path ??
    entry?.href ??
    entry?.image_url ??
    entry?.imageUrl ??
    entry?.video_url ??
    entry?.videoUrl ??
    entry?.file ??
    entry?.original ??
    '';

  return resolveMediaUrl(raw);
}

function appendMediaEntries(list, source) {
  if (source == null) return;
  if (Array.isArray(source)) {
    source.forEach((item) => appendMediaEntries(list, item));
    return;
  }
  if (typeof source === 'object' && !Array.isArray(source)) {
    const url = extractMediaUrl(source);
    if (url) {
      list.push({ ...source, __url: url });
      return;
    }

    const values = Object.values(source);
    if (values.length) {
      values.forEach((item) => appendMediaEntries(list, item));
    }
    return;
  }

  const url = extractMediaUrl(source);
  if (url) {
    list.push({ __url: url });
  }
}

function buildTrainingMediaItems(trainingData) {
  if (!trainingData) return [];

  const entries = [];
  const pushUnique = (collection, seen, item) => {
    if (!item?.src) return;
    if (seen.has(item.src)) return;
    seen.add(item.src);
    collection.push(item);
  };

  appendMediaEntries(entries, trainingData?.video_url);
  appendMediaEntries(entries, trainingData?.videoUrl);
  appendMediaEntries(entries, trainingData?.videos);
  appendMediaEntries(entries, trainingData?.video_urls);
  appendMediaEntries(entries, trainingData?.videoUrls);

  appendMediaEntries(entries, trainingData?.image_url);
  appendMediaEntries(entries, trainingData?.imageUrl);
  appendMediaEntries(entries, trainingData?.images);
  appendMediaEntries(entries, trainingData?.image_urls);
  appendMediaEntries(entries, trainingData?.imageUrls);
  appendMediaEntries(entries, trainingData?.photos);
  appendMediaEntries(entries, trainingData?.photo_urls);
  appendMediaEntries(entries, trainingData?.photoUrls);
  appendMediaEntries(entries, trainingData?.gallery);
  appendMediaEntries(entries, trainingData?.gallery_images);
  appendMediaEntries(entries, trainingData?.galleryImages);
  appendMediaEntries(entries, trainingData?.media);
  appendMediaEntries(entries, trainingData?.media_items);
  appendMediaEntries(entries, trainingData?.mediaItems);

  const videos = [];
  const images = [];
  const seenVideo = new Set();
  const seenImage = new Set();

  entries.forEach((entry) => {
    const src = entry?.__url || extractMediaUrl(entry);
    if (!src) return;
    const type = inferMediaKind(src, entry);
    if (type === 'video') {
      pushUnique(videos, seenVideo, { type: 'video', src });
    } else {
      pushUnique(images, seenImage, { type: 'image', src });
    }
  });

  return [...videos, ...images];
}

function textToArray(value) {
  if (value == null) return [];
  if (Array.isArray(value)) return value;
  return [value];
}

function pickLabelFromObject(obj) {
  if (!obj) return '';
  if (typeof obj === 'string' || typeof obj === 'number') {
    return maybeFixUtf8Mojibake(obj).toString().trim();
  }

  return maybeFixUtf8Mojibake(
    obj?.full_name ??
      obj?.fullName ??
      obj?.name ??
      obj?.title ??
      obj?.username ??
      obj?.login ??
      obj?.label ??
      '',
  ).toString().trim();
}

function extractLabelList(value) {
  return textToArray(value)
    .map((item) => pickLabelFromObject(item))
    .filter(Boolean);
}

function normalizeOptionalText(value) {
  return maybeFixUtf8Mojibake(value ?? '').toString().trim();
}

function normalizePositionKey(value) {
  return maybeFixUtf8Mojibake(value ?? '').toString().trim().toLowerCase();
}

function normalizePositionLabel(value, fallbackKey = '') {
  const raw = maybeFixUtf8Mojibake(value ?? '').toString().trim();
  const key = normalizePositionKey(fallbackKey || raw);
  const map = {
    'доигровка': 'доигровка',
    doigrovka: 'доигровка',
    outside_hitter: 'доигровка',
    wing_spiker: 'доигровка',
    outside: 'доигровка',
    outside_1: 'доигровка',
    outside_2: 'доигровка',
    'цб': 'ЦБ',
    middle_blocker: 'ЦБ',
    cb: 'ЦБ',
    center_blocker: 'ЦБ',
    middle: 'ЦБ',
    middle_1: 'ЦБ',
    middle_2: 'ЦБ',
    'связка': 'связка',
    setter: 'связка',
    setter_spiker: 'связка',
    'диагональный': 'диагональный',
    diagonal: 'диагональный',
    opposite: 'диагональный',
    'либеро': 'либеро',
    libero: 'либеро',
  };

  if (map[key]) return map[key];
  if (raw) return raw;
  return fallbackKey || '';
}

function inferTeamNumberFromText(value) {
  const text = maybeFixUtf8Mojibake(value ?? '').toString().trim().toLowerCase();
  if (!text) return null;

  const compact = text.replace(/[\s_-]+/g, '');
  if (compact === '1' || compact === 'team1' || compact === 'команда1' || compact === 't1') return 1;
  if (compact === '2' || compact === 'team2' || compact === 'команда2' || compact === 't2') return 2;

  if (text === '1' || text === 'team1' || text === 'команда1' || text === 'команда 1') return 1;
  if (text === '2' || text === 'team2' || text === 'команда2' || text === 'команда 2') return 2;

  const teamMatch = text.match(/(?:team|команда)[_\-\s]*([12])/i);
  if (teamMatch) return Number(teamMatch[1]);

  const plainNumber = text.match(/^([12])$/);
  if (plainNumber) return Number(plainNumber[1]);

  return null;
}

function inferTeamNumberFromPositionKey(positionKey) {
  const key = normalizePositionKey(positionKey);
  if (!key) return null;

  const embedded = key.match(/team(?:_|-)?([12])/);
  if (embedded) return Number(embedded[1]);

  const suffix = key.match(/(?:_|-)([12])$/);
  if (suffix) return Number(suffix[1]);

  return null;
}

function buildTeamLabel(teamRaw, teamNumber) {
  const raw = maybeFixUtf8Mojibake(teamRaw ?? '').toString().trim();
  if (raw) {
    const numeric = inferTeamNumberFromText(raw);
    if (numeric) return `Команда ${numeric}`;
    if (/команда/i.test(raw)) return raw;
    return `Команда ${raw}`;
  }
  if (teamNumber) return `Команда ${teamNumber}`;
  return '';
}

function buildPositionLabelWithTeam(positionLabel, teamLabel) {
  const base = maybeFixUtf8Mojibake(positionLabel ?? '').toString().trim();
  if (!base) return '';
  if (!teamLabel) return base;
  if (base.toLowerCase().includes(teamLabel.toLowerCase())) return base;
  return `${base} — ${teamLabel}`;
}

function getPositionOptionDedupKey(item) {
  if (!item?.key) return '';
  const teamPart = normalizePositionKey(item?.teamKey ?? item?.teamLabel ?? item?.teamNumber ?? '');
  return teamPart ? `${item.key}::${teamPart}` : item.key;
}

function positionDisplayLabelFromKey(positionKey, rawLabel = '', teamRaw = '') {
  const key = normalizePositionKey(positionKey);
  if (!key) return '';
  const label = normalizePositionLabel(rawLabel || key, key);
  const teamNumber = inferTeamNumberFromText(teamRaw) ?? inferTeamNumberFromPositionKey(key);
  const teamLabel = buildTeamLabel(teamRaw, teamNumber);
  return buildPositionLabelWithTeam(label, teamLabel);
}

function normalizePositionCount(value) {
  const n = toNumber(value);
  return Number.isFinite(n) ? Math.max(0, Math.trunc(n)) : null;
}

function normalizePositionOption(entry, fallbackKey = '') {
  if (entry == null) return null;

  if (typeof entry === 'string' || typeof entry === 'number') {
    const label = normalizePositionLabel(entry, fallbackKey);
    const key = normalizePositionKey(entry || fallbackKey || label);
    if (!key) return null;
    const teamNumber = inferTeamNumberFromPositionKey(key);
    const teamLabel = buildTeamLabel('', teamNumber);
    const teamKey = normalizePositionKey(teamLabel || (teamNumber ? `team_${teamNumber}` : ''));
    return {
      key,
      selectionKey: teamKey ? `${key}::${teamKey}` : key,
      label: label || key,
      displayLabel: buildPositionLabelWithTeam(label || key, teamLabel),
      free: null,
      freeMain: null,
      freeReserve: null,
      total: null,
      totalMain: null,
      totalReserve: null,
      teamLabel: teamLabel || '',
      teamNumber,
      teamKey: teamKey || '',
    };
  }

  if (typeof entry !== 'object') return null;

  const keyRaw =
    entry?.key ??
    entry?.position_key ??
    entry?.positionKey ??
    entry?.code ??
    entry?.slug ??
    entry?.id ??
    fallbackKey ??
    '';
  const labelRaw =
    entry?.label ??
    entry?.title ??
    entry?.name ??
    entry?.position_name ??
    entry?.positionName ??
    entry?.display_name ??
    entry?.displayName ??
    entry?.text ??
    '';
  const freeRaw =
    entry?.free ??
    entry?.free_slots ??
    entry?.freeSlots ??
    entry?.available ??
    entry?.available_count ??
    entry?.availableCount ??
    entry?.slots_available ??
    entry?.slotsAvailable ??
    entry?.remaining ??
    entry?.remaining_slots ??
    entry?.remainingSlots ??
    entry?.count ??
    entry?.qty ??
    null;
  const freeMainRaw =
    entry?.free_main ??
    entry?.freeMain ??
    entry?.main_free ??
    entry?.mainFree ??
    freeRaw;
  const freeReserveRaw =
    entry?.free_reserve ??
    entry?.freeReserve ??
    entry?.reserve_free ??
    entry?.reserveFree ??
    null;
  const totalRaw =
    entry?.total ??
    entry?.total_slots ??
    entry?.totalSlots ??
    entry?.capacity ??
    entry?.max ??
    entry?.limit ??
    null;
  const totalMainRaw =
    entry?.capacity_main ??
    entry?.capacityMain ??
    entry?.main_capacity ??
    entry?.mainCapacity ??
    totalRaw;
  const totalReserveRaw =
    entry?.capacity_reserve ??
    entry?.capacityReserve ??
    entry?.reserve_capacity ??
    entry?.reserveCapacity ??
    null;
  const teamRaw =
    entry?.team ??
    entry?.team_id ??
    entry?.teamId ??
    entry?.team_key ??
    entry?.teamKey ??
    entry?.team_name ??
    entry?.teamName ??
    entry?.side ??
    entry?.side_name ??
    entry?.sideName ??
    entry?.group ??
    '';

  const key = normalizePositionKey(keyRaw || labelRaw || fallbackKey);
  if (!key) return null;

  const label = normalizePositionLabel(labelRaw || keyRaw || fallbackKey, key);
  const freeMain = normalizePositionCount(freeMainRaw);
  const freeReserve = normalizePositionCount(freeReserveRaw);
  const totalMain = normalizePositionCount(totalMainRaw);
  const totalReserve = normalizePositionCount(totalReserveRaw);
  const teamNumber = inferTeamNumberFromText(teamRaw) ?? inferTeamNumberFromPositionKey(key);
  const teamLabel = buildTeamLabel(teamRaw, teamNumber);
  const teamKey = normalizePositionKey(teamRaw || (teamNumber ? `team_${teamNumber}` : teamLabel));
  const selectionKey = teamKey ? `${key}::${teamKey}` : key;
  const displayLabel = buildPositionLabelWithTeam(label || key, teamLabel);

  return {
    key,
    selectionKey,
    label: label || key,
    displayLabel: displayLabel || label || key,
    free: freeMain,
    freeMain,
    freeReserve,
    total: totalMain,
    totalMain,
    totalReserve,
    teamLabel: teamLabel || '',
    teamNumber,
    teamKey: teamKey || '',
  };
}

function extractPositionOptionsFromSource(source) {
  if (source == null) return [];

  const items = [];

  if (Array.isArray(source)) {
    source.forEach((item, index) => {
      const normalized = normalizePositionOption(item, String(index));
      if (normalized) items.push(normalized);
    });
  } else if (typeof source === 'object') {
    Object.entries(source).forEach(([key, value]) => {
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        const normalized = normalizePositionOption({ key, ...value }, key);
        if (normalized) items.push(normalized);
        return;
      }

      const normalized = normalizePositionOption(
        {
          key,
          label: key,
          free: value,
        },
        key,
      );
      if (normalized) items.push(normalized);
    });
  } else {
    const normalized = normalizePositionOption(source);
    if (normalized) items.push(normalized);
  }

  const dedup = new Map();
  items.forEach((item) => {
    const dedupKey = getPositionOptionDedupKey(item);
    const prev = dedup.get(dedupKey);
    if (!prev) {
      dedup.set(dedupKey, item);
      return;
    }

    const betterFree = prev.free != null ? prev.free : item.free;
    const betterTotal = prev.total ?? item.total ?? null;
    const betterLabel = prev.label || item.label || item.key;
    dedup.set(dedupKey, {
      ...prev,
      ...item,
      label: betterLabel,
      selectionKey: item.selectionKey || prev.selectionKey || dedupKey,
      displayLabel: item.displayLabel || prev.displayLabel || betterLabel,
      free: betterFree,
      total: betterTotal,
    });
  });

  return Array.from(dedup.values())
    .filter((item) => {
      if (item.free == null) return true;
      return item.free > 0;
    })
    .map((item) => ({
      ...item,
      label: normalizePositionLabel(item.label, item.key) || item.key,
      displayLabel:
        item.displayLabel ||
        buildPositionLabelWithTeam(normalizePositionLabel(item.label, item.key) || item.key, item.teamLabel),
      selectionKey: item.selectionKey || getPositionOptionDedupKey(item) || item.key,
    }));
}

function mergePositionOptionLists(lists) {
  const dedup = new Map();

  lists.filter(Boolean).forEach((list) => {
    list.forEach((item) => {
      if (!item?.key) return;
      const dedupKey = getPositionOptionDedupKey(item);
      const prev = dedup.get(dedupKey);
      if (!prev) {
        dedup.set(dedupKey, item);
        return;
      }

      dedup.set(dedupKey, {
        ...prev,
        ...item,
        label: item.label || prev.label || item.key,
        selectionKey: item.selectionKey || prev.selectionKey || dedupKey,
        displayLabel: item.displayLabel || prev.displayLabel || item.label || prev.label || item.key,
        free: prev.free != null ? prev.free : item.free,
        total: prev.total != null ? prev.total : item.total,
      });
    });
  });

  return Array.from(dedup.values())
    .filter((item) => {
      if (item.free == null) return true;
      return item.free > 0;
    })
    .map((item) => ({
      ...item,
      label: normalizePositionLabel(item.label, item.key) || item.key,
      displayLabel:
        item.displayLabel ||
        buildPositionLabelWithTeam(normalizePositionLabel(item.label, item.key) || item.key, item.teamLabel),
      selectionKey: item.selectionKey || getPositionOptionDedupKey(item) || item.key,
    }));
}

function extractPositionOptionsFromTraining(trainingData) {
  const available = extractPositionOptionsFromSource(
    trainingData?.available_positions ??
      trainingData?.availablePositions ??
      trainingData?.available_positions_list ??
      trainingData?.availablePositionsList ??
      null,
  );
  const slots = extractPositionOptionsFromSource(
    trainingData?.position_slots ?? trainingData?.positionSlots ?? trainingData?.positions ?? null,
  );

  return mergePositionOptionLists([available, slots]);
}

function extractPositionOptionsFromPayload(payload) {
  const candidates = [
    payload,
    payload?.detail,
    payload?.details,
    payload?.detail?.details,
    payload?.error,
    payload?.error?.detail,
    payload?.error?.details,
    payload?.error?.detail?.details,
  ];

  for (const candidate of candidates) {
    if (!candidate) continue;
    const source =
      candidate?.available_positions ??
      candidate?.availablePositions ??
      candidate?.position_slots ??
      candidate?.positionSlots ??
      candidate?.available_positions_list ??
      candidate?.availablePositionsList ??
      null;
    const options = mergePositionOptionLists([
      extractPositionOptionsFromSource(candidate?.available_positions ?? candidate?.availablePositions ?? candidate?.available_positions_list ?? candidate?.availablePositionsList ?? null),
      extractPositionOptionsFromSource(candidate?.position_slots ?? candidate?.positionSlots ?? null),
      extractPositionOptionsFromSource(source),
    ]);
    if (options.length) return options;
  }

  return [];
}

function getPositionErrorMessage(payload) {
  const candidates = [payload, payload?.detail, payload?.details, payload?.error, payload?.error?.detail, payload?.error?.details];

  for (const candidate of candidates) {
    if (!candidate) continue;
    if (typeof candidate === 'string') return maybeFixUtf8Mojibake(candidate).toString().trim();
    if (typeof candidate.message === 'string' && candidate.message.trim()) {
      return maybeFixUtf8Mojibake(candidate.message).toString().trim();
    }
    if (typeof candidate.detail === 'string' && candidate.detail.trim()) {
      return maybeFixUtf8Mojibake(candidate.detail).toString().trim();
    }
    if (candidate.error && typeof candidate.error.message === 'string' && candidate.error.message.trim()) {
      return maybeFixUtf8Mojibake(candidate.error.message).toString().trim();
    }
  }

  return '';
}

function getBookingPositionTitle(option) {
  const key = option?.key ?? '';
  const normalized = normalizePositionLabel(
    option?.positionLabel ?? option?.position_label ?? option?.label ?? key,
    key,
  );
  return normalized || (option?.label || key || 'Позиция');
}

function resolveAvatarUrl(raw) {
  const value = maybeFixUtf8Mojibake(raw ?? '').toString().trim();
  if (!value) return '';
  return resolveAssetUrl(value);
}

function AvatarImage({ src, alt, className, fallback }) {
  const [failedSrc, setFailedSrc] = useState('');
  if (!src || failedSrc === src) return fallback;

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      loading="lazy"
      onError={() => setFailedSrc(src)}
    />
  );
}

function tgUsernamePretty(raw) {
  const value = maybeFixUtf8Mojibake(raw ?? '').toString().trim();
  if (!value) return '';
  return value.startsWith('@') ? value : `@${value}`;
}

function openTelegramByUsername(username) {
  const clean = maybeFixUtf8Mojibake(username ?? '').toString().trim().replace(/^@/, '');
  if (!clean) return;
  const url = `https://t.me/${clean}`;
  try {
    const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : null;
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(url);
      return;
    }
    if (tg?.openLink) {
      tg.openLink(url);
      return;
    }
  } catch {
    // ignore and fallback to window.open
  }
  try {
    window.open(url, '_blank', 'noopener,noreferrer');
  } catch {
    // ignore
  }
}

const PENDING_PAYMENT_KEY_PREFIX = 'pending.yookassa.enrollment.';

function getPendingPaymentStorageKey(trainingId) {
  return `${PENDING_PAYMENT_KEY_PREFIX}${String(trainingId ?? '')}`;
}

function readPendingPaymentId(trainingId) {
  if (!trainingId) return '';
  try {
    return localStorage.getItem(getPendingPaymentStorageKey(trainingId)) || '';
  } catch {
    return '';
  }
}

function writePendingPaymentId(trainingId, paymentId) {
  if (!trainingId || !paymentId) return;
  try {
    localStorage.setItem(getPendingPaymentStorageKey(trainingId), String(paymentId));
  } catch {
    // ignore
  }
}

function clearPendingPaymentId(trainingId) {
  if (!trainingId) return;
  try {
    localStorage.removeItem(getPendingPaymentStorageKey(trainingId));
  } catch {
    // ignore
  }
}

export default function TrainingDetail({ trainingId, onBack, onChanged }) {
  const [training, setTraining] = useState(null);
  const [locationLabel, setLocationLabel] = useState('');
  const [locationObj, setLocationObj] = useState(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [pendingPaymentId, setPendingPaymentId] = useState('');
  const [checkingPayment, setCheckingPayment] = useState(false);
  const [paymentHint, setPaymentHint] = useState('');

  const [bookingOpen, setBookingOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [banInfoOpen, setBanInfoOpen] = useState(false);
  const [playerModalOpen, setPlayerModalOpen] = useState(false);
  const [playerModalUserId, setPlayerModalUserId] = useState(null);
  const [playerModalLoading, setPlayerModalLoading] = useState(false);
  const [playerModalError, setPlayerModalError] = useState('');
  const [playerModalProfile, setPlayerModalProfile] = useState(null);
  const [bookingError, setBookingError] = useState('');
  const [bookingPositionOptions, setBookingPositionOptions] = useState([]);
  const [bookingSelectedPositionKey, setBookingSelectedPositionKey] = useState('');
  const videoRef = useRef(null);

  const openExternalLink = (url) => {
    if (!url) return;
    const tg = window?.Telegram?.WebApp;
    if (tg?.openLink) {
      try {
        tg.openLink(url);
        return;
      } catch {
        // fallback РЅРёР¶Рµ
      }
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const fetchLocationById = async (locId) => {
    // Р’РђР–РќРћ: Сѓ С‚РµР±СЏ РќР•Рў /api/v1/locations/{id}, РїРѕСЌС‚РѕРјСѓ СЂР°Р±РѕС‚Р°РµРј С‚РѕР»СЊРєРѕ СЃРѕ СЃРїРёСЃРєР°РјРё.
    // РќРѕ СЃРµР№С‡Р°СЃ СЃРїРёСЃРєРё РІРѕР·РІСЂР°С‰Р°СЋС‚ Р»РёС€СЊ {id}, Р±РµР· name/address/coords вЂ” СЌС‚Рѕ РѕРіСЂР°РЅРёС‡РµРЅРёРµ Р±СЌРєР°/Р‘Р”.
    const urls = [
      '/api/v1/locations?limit=500&offset=0&only_with_trainings=true',
      '/api/v1/locations?limit=500&offset=0',
    ];

    for (const url of urls) {
      try {
        const locRes = await apiFetch(url);
        const items = Array.isArray(locRes) ? locRes : Array.isArray(locRes?.items) ? locRes.items : [];
        const found = items.find((x) => sameId(x?.id ?? x?.location_id ?? x?.locationId, locId));
        if (found) return found;
      } catch {
        // ignore
      }
    }
    return null;
  };

  const load = async () => {
    if (!trainingId) return;

    try {
      setLoading(true);
      setError('');

      const tRaw = await apiFetch(`/api/v1/trainings/${trainingId}`);

      // Р§РёРЅРёРј РїРѕС‚РµРЅС†РёР°Р»СЊРЅС‹Рµ РєСЂР°РєРѕР·СЏР±СЂС‹ РЅР° РєР»СЋС‡РµРІС‹С… С‚РµРєСЃС‚Р°С…
      const t = {
        ...tRaw,
        title: maybeFixUtf8Mojibake(tRaw?.title),
        description: maybeFixUtf8Mojibake(tRaw?.description),
        coach_name: maybeFixUtf8Mojibake(tRaw?.coach_name),
      };

      let locLabel = '';
      let locObj = null;

      // 1) РџС‹С‚Р°РµРјСЃСЏ РґРѕСЃС‚Р°С‚СЊ Р°РґСЂРµСЃ/РЅР°Р·РІР°РЅРёРµ РёР· С‚СЂРµРЅРёСЂРѕРІРєРё (РµСЃР»Рё Р±РµРє РЅР°С‡РЅРµС‚ СЌС‚Рѕ РѕС‚РґР°РІР°С‚СЊ)
      locLabel = pickFirstNonEmptyString([
        t?.address,
        t?.location_address,
        t?.locationAddress,
        t?.location_name,
        t?.locationName,
        t?.location_title,
        t?.locationTitle,
        t?.place_name,
        t?.placeName,
        t?.place_title,
        t?.placeTitle,
        t?.location, // РјРѕР¶РµС‚ Р±С‹С‚СЊ СЃС‚СЂРѕРєРѕР№ РёР»Рё РѕР±СЉРµРєС‚РѕРј
        t?.place, // РјРѕР¶РµС‚ Р±С‹С‚СЊ СЃС‚СЂРѕРєРѕР№ РёР»Рё РѕР±СЉРµРєС‚РѕРј
      ]);

      // 2) Р•СЃР»Рё location/place РѕР±СЉРµРєС‚РѕРј вЂ” СЃРѕС…СЂР°РЅСЏРµРј
      const directLoc = t?.location ?? t?.place ?? null;
      if (directLoc) {
        const directLabel = normalizeLocationLabel(directLoc);
        if (directLabel) locLabel = directLabel;
        if (typeof directLoc === 'object') locObj = directLoc;
      }

      // 3) Р•СЃР»Рё РµСЃС‚СЊ location_id вЂ” РїСЂРѕР±СѓРµРј РЅР°Р№С‚Рё РІ СЃРїРёСЃРєРµ
      const locId = t?.location_id ?? t?.locationId ?? null;
      if (locId != null) {
        const found = await fetchLocationById(locId);
        if (found) {
          // СЃРµР№С‡Р°СЃ found = {id}, РЅРѕ РµСЃР»Рё РїРѕР·Р¶Рµ Р±РµРє РЅР°С‡РЅРµС‚ РѕС‚РґР°РІР°С‚СЊ РїРѕР»СЏ вЂ” С‚СѓС‚ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё Р·Р°СЂР°Р±РѕС‚Р°РµС‚
          const lbl = normalizeLocationLabel(found);
          if (lbl) locLabel = lbl;
          locObj = found;
        }

        // Р•СЃР»Рё РІРѕРѕР±С‰Рµ РЅРёС‡РµРіРѕ РЅРµС‚ вЂ” РїРѕРєР°Р·С‹РІР°РµРј СЋР·РµСЂ-С„СЂРµРЅРґР»Рё РїРѕРґРїРёСЃСЊ (РЅРѕ РќР• РёСЃРїРѕР»СЊР·СѓРµРј РµС‘ РґР»СЏ РєР°СЂС‚С‹)
        if (!locLabel) locLabel = `Локация #${locId}`;
      }

      setTraining(t);
      setLocationLabel(locLabel);
      setLocationObj(locObj);
    } catch (err) {
      setError(err?.message || 'Не удалось загрузить тренировку');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (cancelled) return;
      await load();
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trainingId]);

  useEffect(() => {
    setPendingPaymentId(readPendingPaymentId(trainingId));
    setPaymentHint('');
  }, [trainingId]);

  const mediaItems = useMemo(() => buildTrainingMediaItems(training), [training]);
  const mediaPosterUrl = useMemo(() => {
    const firstImage = mediaItems.find((item) => item.type === 'image');
    if (firstImage?.src) return firstImage.src;
    return resolveMediaUrl(training?.image_url) || '';
  }, [mediaItems, training?.image_url]);
  const activeMediaItem = useMemo(() => {
    const firstImage = mediaItems.find((item) => item.type === 'image');
    return firstImage || mediaItems[0] || null;
  }, [mediaItems]);

  const trainingType = useMemo(() => {
    return maybeFixUtf8Mojibake(
      training?.type ??
        training?.training_type ??
        training?.trainingType ??
        training?.sport_type ??
        training?.sportType ??
        training?.format ??
        '',
    )
      .toString()
      .trim()
      .toLowerCase();
  }, [training?.format, training?.sportType, training?.sport_type, training?.trainingType, training?.training_type, training?.type]);

  const isAmpLuaTraining =
    trainingType.includes('амплуа') || trainingType.includes('amplua') || trainingType.includes('amp lua');
  const ampLuaTrainingPositionOptions = useMemo(() => extractPositionOptionsFromTraining(training), [training]);

  useEffect(() => {
    if (!bookingOpen || !isAmpLuaTraining) {
      setBookingError('');
      setBookingPositionOptions([]);
      setBookingSelectedPositionKey('');
      return;
    }

    setBookingError('');
    setBookingPositionOptions(ampLuaTrainingPositionOptions);
    setBookingSelectedPositionKey((prev) => {
      const prevSelection = normalizePositionKey(prev);
      if (prevSelection && ampLuaTrainingPositionOptions.some((item) => item.selectionKey === prevSelection)) {
        return prevSelection;
      }

      const preferredKey = normalizePositionKey(training?.user_position_key ?? '');
      if (preferredKey) {
        const preferredOption = ampLuaTrainingPositionOptions.find((item) => item.key === preferredKey);
        if (preferredOption?.selectionKey) return preferredOption.selectionKey;
      }

      return '';
    });
  }, [ampLuaTrainingPositionOptions, bookingOpen, isAmpLuaTraining, training?.user_position_key]);

  useEffect(() => {
    if (!activeMediaItem || activeMediaItem.type !== 'video') return;
    const node = videoRef.current;
    if (!node) return;

    const play = async () => {
      try {
        await node.play();
      } catch {
        // autoplay РјРѕР¶РµС‚ Р±С‹С‚СЊ РѕРіСЂР°РЅРёС‡РµРЅ РєР»РёРµРЅС‚РѕРј
      }
    };

    play();
  }, [activeMediaItem, activeMediaItem?.src, activeMediaItem?.type]);

  const openParticipantProfile = (userId) => {
    if (!userId) return;
    setPlayerModalUserId(Number(userId));
    setPlayerModalOpen(true);
    setPlayerModalLoading(true);
    setPlayerModalError('');
    setPlayerModalProfile(null);
  };

  const closeParticipantProfile = () => {
    setPlayerModalOpen(false);
    setPlayerModalUserId(null);
    setPlayerModalLoading(false);
    setPlayerModalError('');
    setPlayerModalProfile(null);
  };

  useEffect(() => {
    let alive = true;
    async function loadParticipantProfile() {
      if (!playerModalOpen || !playerModalUserId) return;
      try {
        setPlayerModalLoading(true);
        setPlayerModalError('');
        const res = await apiFetch(`/api/v1/profile/${playerModalUserId}`);
        const profile = res?.item ?? res ?? null;
        if (!alive) return;
        setPlayerModalProfile(profile);
      } catch (err) {
        if (!alive) return;
        setPlayerModalError(err?.message || 'Не удалось загрузить профиль игрока');
      } finally {
        if (alive) setPlayerModalLoading(false);
      }
    }
    loadParticipantProfile();
    return () => {
      alive = false;
    };
  }, [playerModalOpen, playerModalUserId]);

  const playerModalView = useMemo(() => {
    if (!playerModalProfile) return null;
    const name = participantDisplayName(playerModalProfile);
    const avatarLetter = participantAvatarLetter(playerModalProfile);
    const avatarUrl = resolveAvatarUrl(playerModalProfile?.avatar_url);
    const levelName = maybeFixUtf8Mojibake(playerModalProfile?.level_name ?? '').toString().trim();
    const rating = Number(playerModalProfile?.rating ?? 0) || 0;
    const cups = Number(playerModalProfile?.cups ?? 0) || 0;
    const username = maybeFixUtf8Mojibake(playerModalProfile?.username ?? '').toString().trim();
    return {
      name,
      avatarLetter,
      avatarUrl,
      levelName: levelName || '—',
      rating,
      cups,
      telegram: tgUsernamePretty(username),
      telegramRaw: username,
    };
  }, [playerModalProfile]);

  const selectedBookingPosition = useMemo(
    () =>
      bookingPositionOptions.find(
        (item) => item.selectionKey === normalizePositionKey(bookingSelectedPositionKey),
      ) ?? null,
    [bookingPositionOptions, bookingSelectedPositionKey],
  );
  const bookingPositionGroups = useMemo(() => {
    const groups = {
      team1: [],
      team2: [],
      other: [],
    };

    bookingPositionOptions.forEach((option) => {
      const teamNumber =
        Number(option?.teamNumber) ||
        inferTeamNumberFromText(option?.teamLabel) ||
        inferTeamNumberFromText(option?.teamKey) ||
        inferTeamNumberFromPositionKey(option?.key);

      if (teamNumber === 1) {
        groups.team1.push(option);
      } else if (teamNumber === 2) {
        groups.team2.push(option);
      } else {
        groups.other.push(option);
      }
    });

    const byLabel = (a, b) => {
      const aLabel = normalizePositionLabel(a?.label ?? '', a?.key ?? '');
      const bLabel = normalizePositionLabel(b?.label ?? '', b?.key ?? '');
      return aLabel.localeCompare(bLabel, 'ru');
    };
    groups.team1.sort(byLabel);
    groups.team2.sort(byLabel);
    groups.other.sort(byLabel);

    return groups;
  }, [bookingPositionOptions]);
  const renderBookingPositionOption = (option) => {
    const optionSelectionKey = option.selectionKey || option.key;
    const isSelected = normalizePositionKey(optionSelectionKey) === normalizePositionKey(bookingSelectedPositionKey);
    const freeMain = option?.freeMain ?? option?.free_main ?? option?.free;
    const freeReserve = option?.freeReserve ?? option?.free_reserve;
    let freeLabel = freeMain != null ? `основа: ${freeMain}` : 'основа: доступно';
    if (freeReserve != null) {
      freeLabel += ` · резерв: ${freeReserve}`;
    }
    const optionTitle = getBookingPositionTitle(option);

    return (
      <button
        key={optionSelectionKey}
        type="button"
        className={`booking-position-option${isSelected ? ' is-selected' : ''}`}
        onClick={() => {
          setBookingSelectedPositionKey(optionSelectionKey);
          setBookingError('');
        }}
      >
        <span className="booking-position-option-main">
          <span className="booking-position-option-label">{optionTitle}</span>
          <span className="booking-position-option-meta">{freeLabel}</span>
        </span>
        {isSelected ? <span className="booking-position-option-check">✓</span> : null}
      </button>
    );
  };

  const startAt = useMemo(
    () => parseDate(training?.starts_at ?? training?.start_at ?? training?.startsAt ?? training?.startAt),
    [training],
  );

  const duration = useMemo(() => toNumber(training?.duration_minutes ?? training?.durationMinutes) ?? 0, [training]);

  const endAt = useMemo(() => {
    if (!startAt || !duration) return null;
    return new Date(startAt.getTime() + duration * 60_000);
  }, [startAt, duration]);

  const timePill = useMemo(() => formatTime(startAt), [startAt]);

  const timeRange = useMemo(() => {
    if (!startAt) return '';
    const a = formatTime(startAt);
    const b = endAt ? formatTime(endAt) : '';
    return b ? `${a}–${b}` : a;
  }, [startAt, endAt]);

  const dateLabel = useMemo(() => formatDate(startAt), [startAt]);
  const isTrainingFinished = useMemo(() => {
    if (!startAt) return false;
    const endAtMs = (endAt ?? startAt).getTime();
    return Date.now() >= endAtMs;
  }, [startAt, endAt]);

  const levelChips = useMemo(() => buildLevelChips(training), [training]);

  const tiers = useMemo(() => {
    const raw = Array.isArray(training?.price_tiers) ? training.price_tiers : [];
    const copy = [...raw];
    copy.sort((a, b) => (toNumber(a?.sort_order) ?? 0) - (toNumber(b?.sort_order) ?? 0));
    return copy;
  }, [training]);

  const peopleRange = useMemo(() => {
    const nums = tiers.map((x) => parseTierPeople(x?.title)).filter((x) => x != null);
    if (!nums.length) return { min: null, max: null };
    return { min: Math.min(...nums), max: Math.max(...nums) };
  }, [tiers]);

  const participantsMain = useMemo(
    () => (Array.isArray(training?.participants_main) ? training.participants_main : []),
    [training],
  );
  const participantsReserve = useMemo(
    () => (Array.isArray(training?.participants_reserve) ? training.participants_reserve : []),
    [training],
  );
  const participantsTotal = useMemo(() => {
    const fromApi = toNumber(training?.participants_total);
    if (fromApi != null) return fromApi;
    return participantsMain.length + participantsReserve.length;
  }, [training, participantsMain.length, participantsReserve.length]);

  const capacityMain = useMemo(() => toNumber(training?.capacity_main) ?? 0, [training]);
  const capacityReserve = useMemo(() => toNumber(training?.capacity_reserve) ?? 0, [training]);

  const freePlaces = useMemo(() => {
    const fp = toNumber(training?.free_places);
    if (fp != null) return fp;
    const occupied = toNumber(training?.occupied_main) ?? 0;
    const left = capacityMain - occupied;
    return left >= 0 ? left : 0;
  }, [training, capacityMain]);
  const reserveFreePlaces = useMemo(() => {
    const occupiedReserve = toNumber(training?.occupied_reserve) ?? participantsReserve.length;
    const left = capacityReserve - occupiedReserve;
    return left >= 0 ? left : 0;
  }, [training, participantsReserve.length, capacityReserve]);

  const isEnrolled = useMemo(() => {
    const st = (training?.user_enrollment_status ?? '').toString();
    return st === 'main' || st === 'reserve';
  }, [training]);

  const enrolledStatusLabel = useMemo(() => {
    const st = (training?.user_enrollment_status ?? '').toString();
    if (st === 'main') return 'Вы записаны';
    if (st === 'reserve') return 'Вы в резерве';
    return '';
  }, [training]);

  const canEnroll = Boolean(training?.can_enroll);
  const canEnrollReserve = Boolean(training?.can_enroll_reserve);
  const isReserveAvailable = Boolean(training?.is_reserve_available);
  const userHasActiveBan = Boolean(training?.user_has_active_ban);
  const userBanReason = maybeFixUtf8Mojibake(
    training?.user_active_ban_reason || training?.user_active_ban_text || '',
  ).toString().trim();
  const userBanUntil = useMemo(() => parseDate(training?.user_active_ban_until), [training]);
  const userLevelBlockReason = maybeFixUtf8Mojibake(training?.user_level_block_reason || '').toString().trim();
  const hasLevelBlock = !isEnrolled && Boolean(userLevelBlockReason);

  const cancelDeadlineAt = useMemo(() => parseDate(training?.cancel_deadline_at), [training]);

  const canCancel = useMemo(() => {
    const apiCan = Boolean(training?.can_cancel);
    if (!apiCan) return false;
    if (!cancelDeadlineAt) return apiCan;
    return Date.now() <= cancelDeadlineAt.getTime();
  }, [training, cancelDeadlineAt]);

  const cancelBlockedHint = useMemo(() => {
    if (!isEnrolled) return '';
    if (canCancel) return '';
    return 'Отмена недоступна менее чем за 2 часа до начала тренировки.';
  }, [isEnrolled, canCancel]);

  // --- Yandex maps widget ---
  const coords = useMemo(() => {
    const a = extractLatLon(training);
    if (a.lat != null && a.lon != null) return a;
    const b = extractLatLon(locationObj);
    if (b.lat != null && b.lon != null) return b;
    return { lat: null, lon: null };
  }, [training, locationObj]);

  // РќР• РїС‹С‚Р°РµРјСЃСЏ СЃС‚СЂРѕРёС‚СЊ РєР°СЂС‚Сѓ РїРѕ Р·Р°РіР»СѓС€РєРµ "Р›РѕРєР°С†РёСЏ #1"
  const mapTextLabel = useMemo(() => {
    const s = (locationLabel || '').trim();
    if (!s) return '';
    if (/^локац/i.test(s) && /\d+$/.test(s)) return '';
    return s;
  }, [locationLabel]);


  const backendMapWidgetSrc = useMemo(() => {
    return (
      training?.maps?.widget_url ||
      training?.maps?.widgetUrl ||
      training?.yandex_widget_url ||
      training?.yandexWidgetUrl ||
      ''
    );
  }, [training]);

  const backendRouteHref = useMemo(() => {
    return (
      training?.maps?.route_url ||
      training?.maps?.routeUrl ||
      training?.yandex_route_url ||
      training?.yandexRouteUrl ||
      ''
    );
  }, [training]);

  const yandexMapSrc = useMemo(() => {
    if (backendMapWidgetSrc) return backendMapWidgetSrc;
    if (coords.lat != null && coords.lon != null) {
      const ll = `${coords.lon},${coords.lat}`; // ll = lon,lat
      return `https://yandex.ru/map-widget/v1/?ll=${encodeURIComponent(ll)}&z=15&pt=${encodeURIComponent(
        ll,
      )},pm2rdm&lang=ru_RU`;
    }
    if (mapTextLabel) {
      return `https://yandex.ru/map-widget/v1/?text=${encodeURIComponent(mapTextLabel)}&z=15&lang=ru_RU`;
    }
    return '';
  }, [backendMapWidgetSrc, coords, mapTextLabel]);

  const yandexRouteHref = useMemo(() => {
    if (backendRouteHref) return backendRouteHref;
    if (coords.lat != null && coords.lon != null) {
      return `https://yandex.ru/maps/?mode=routes&rtext=~${coords.lat},${coords.lon}&rtt=auto`;
    }
    if (mapTextLabel) {
      return `https://yandex.ru/maps/?mode=routes&rtext=~${encodeURIComponent(mapTextLabel)}&rtt=auto`;
    }
    return '';
  }, [backendRouteHref, coords, mapTextLabel]);


  const calendarHref = useMemo(() => {
    return (
      training?.calendar?.google_url ||
      training?.calendar?.googleUrl ||
      training?.calendar_google_url ||
      training?.calendarGoogleUrl ||
      training?.calendar?.ics_url ||
      training?.calendar?.icsUrl ||
      training?.calendar_ics_url ||
      training?.calendarIcsUrl ||
      ''
    );
  }, [training]);

  const enrollButtonLabel = useMemo(() => {
    if (pendingPaymentId && !isEnrolled) return 'Проверить оплату';
    if (isTrainingFinished) return 'Тренировка завершена';
    if (isEnrolled) return 'Отменить запись';
    if (userHasActiveBan) return 'Вы в бане';
    if (hasLevelBlock) return 'Уровень не подходит';
    if (canEnroll) return 'Записаться';
    if (canEnrollReserve && isReserveAvailable) return 'Записаться в резерв';
    return 'Запись недоступна';
  }, [isEnrolled, pendingPaymentId, isTrainingFinished, userHasActiveBan, hasLevelBlock, canEnroll, canEnrollReserve, isReserveAvailable]);

  const enrollButtonDisabled = useMemo(() => {
    if (loading || saving || checkingPayment) return true;
    if (pendingPaymentId) return false;
    if (isTrainingFinished) return true;
    if (isEnrolled) return !canCancel;
    if (hasLevelBlock) return true;
    if (userHasActiveBan) return false;
    if (canEnroll) return false;
    if (canEnrollReserve && isReserveAvailable) return false;
    return true;
  }, [loading, saving, checkingPayment, pendingPaymentId, isTrainingFinished, isEnrolled, canCancel, hasLevelBlock, userHasActiveBan, canEnroll, canEnrollReserve, isReserveAvailable]);

  const priceLabel = useMemo(() => {
    const p = training?.final_price ?? training?.price;
    const n = toNumber(p);
    if (n == null) return '';
    return `${Math.round(n)} ₽`;
  }, [training]);

  const adminNames = useMemo(() => {
    return [
      ...extractLabelList(training?.administrators),
      ...extractLabelList(training?.admins),
      ...extractLabelList(training?.admin_names),
      ...extractLabelList(training?.responsibles),
      ...extractLabelList(training?.organizers),
      ...extractLabelList(training?.curators),
    ].filter((value, index, array) => array.indexOf(value) === index);
  }, [training]);

  const additionalNotes = useMemo(() => {
    const candidates = [
      normalizeOptionalText(training?.rules_text),
      normalizeOptionalText(training?.additional_text),
      normalizeOptionalText(training?.notes),
      normalizeOptionalText(training?.comment),
      normalizeOptionalText(training?.extra_info),
    ].filter(Boolean);
    return candidates[0] || '';
  }, [training]);

  const checkPaymentStatus = async ({ silent = false } = {}) => {
    if (!trainingId || !pendingPaymentId) return;

    try {
      setCheckingPayment(true);
      if (!silent) setError('');

      const result = await apiFetch(`/api/v1/payments/enrollments/${encodeURIComponent(pendingPaymentId)}/status`);
      const status = String(result?.status || '').toLowerCase();
      const cancellationReason = String(result?.cancellation_reason || '').trim();

      if (status === 'succeeded') {
        clearPendingPaymentId(trainingId);
        setPendingPaymentId('');
        setPaymentHint('Оплата подтверждена. Запись обновлена.');
        await load();
        onChanged?.();
        return;
      }

      if (status === 'canceled') {
        clearPendingPaymentId(trainingId);
        setPendingPaymentId('');
        setPaymentHint('');
        if (!silent) {
          const reasonSuffix = cancellationReason ? ` (${cancellationReason})` : '';
          setError(`Оплата отменена${reasonSuffix}`);
        }
        return;
      }

      setPaymentHint('Платеж еще в обработке. Повторите проверку через несколько секунд.');
    } catch (err) {
      if (!silent) {
        setError(err?.message || 'Не удалось проверить статус оплаты');
      }
    } finally {
      setCheckingPayment(false);
    }
  };

  useEffect(() => {
    if (!pendingPaymentId || !trainingId || isEnrolled) return;
    let cancelled = false;
    (async () => {
      if (cancelled) return;
      await checkPaymentStatus({ silent: true });
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingPaymentId, trainingId, isEnrolled]);

  useEffect(() => {
    if (!isEnrolled || !trainingId) return;
    clearPendingPaymentId(trainingId);
    setPendingPaymentId('');
    setPaymentHint('');
  }, [isEnrolled, trainingId]);

  const openEnrollFlow = () => {
    if (isEnrolled) {
      if (!canCancel) return;
      setCancelOpen(true);
      return;
    }

    if (pendingPaymentId) {
      checkPaymentStatus();
      return;
    }

    if (userHasActiveBan) {
      setBanInfoOpen(true);
      return;
    }

    if (hasLevelBlock) {
      return;
    }

    if (canEnroll || (canEnrollReserve && isReserveAvailable)) {
      setBookingError('');
      setBookingOpen(true);
    }
  };

  const doEnroll = async () => {
    if (!trainingId) return;
    try {
      setSaving(true);
      setBookingError('');
      setPaymentHint('');

      const payload = {
        training_id: trainingId,
      };

      const tierId = training?.picked_price_tier_id ?? null;
      if (tierId != null) payload.price_tier_id = tierId;

      if (isAmpLuaTraining) {
        const selectedPositionKey =
          normalizePositionKey(selectedBookingPosition?.key) ||
          normalizePositionKey(bookingSelectedPositionKey).split('::')[0] ||
          '';
        if (!selectedPositionKey) {
          setBookingError('Выберите позицию для записи.');
          return;
        }
        payload.position_key = selectedPositionKey;
      }

      try {
        const returnUrl = new URL(window.location.href);
        returnUrl.searchParams.set('training_id', String(trainingId));
        returnUrl.searchParams.set('payment_result', '1');
        payload.return_url = returnUrl.toString();
      } catch {
        // fallback: backend will use default return_url
      }

      const checkout = await apiFetch('/api/v1/payments/enrollments/checkout', {
        method: 'POST',
        body: payload,
      });
      const createdPaymentId = String(checkout?.payment_id || '').trim();
      const confirmationUrl = String(checkout?.confirmation_url || '').trim();

      if (!createdPaymentId || !confirmationUrl) {
        throw new Error('Не удалось получить ссылку на оплату');
      }

      writePendingPaymentId(trainingId, createdPaymentId);
      setPendingPaymentId(createdPaymentId);
      setPaymentHint('Откройте страницу оплаты и после оплаты вернитесь для проверки статуса.');
      setBookingOpen(false);
      openExternalLink(confirmationUrl);
    } catch (err) {
      const payload = err?.payload ?? null;
      const availableFromError = extractPositionOptionsFromPayload(payload);
      if (availableFromError.length) {
        setBookingPositionOptions(availableFromError);
        setBookingSelectedPositionKey((prev) => {
          const prevSelection = normalizePositionKey(prev);
          if (prevSelection && availableFromError.some((item) => item.selectionKey === prevSelection)) {
            return prevSelection;
          }

          const preferred = normalizePositionKey(training?.user_position_key ?? '');
          if (preferred) {
            const preferredOption = availableFromError.find((item) => item.key === preferred);
            if (preferredOption?.selectionKey) return preferredOption.selectionKey;
          }

          return '';
        });
      }

      const friendlyMessage = getPositionErrorMessage(payload) || err?.message || 'Не удалось записаться';
      if (availableFromError.length) {
        setBookingError(
          friendlyMessage.includes('пози')
            ? friendlyMessage
            : 'Выбранная позиция больше недоступна. Выберите другую позицию из списка ниже.',
        );
        setBookingOpen(true);
        return;
      }

      setBookingError(friendlyMessage);
    } finally {
      setSaving(false);
    }
  };

  const doCancel = async () => {
    const enrollmentId = training?.user_enrollment_id ?? null;
    if (!enrollmentId) {
      setError('Не удалось отменить: отсутствует enrollment_id');
      return;
    }

    try {
      setSaving(true);
      await apiFetch(`/api/v1/enrollments/${enrollmentId}/cancel`, { method: 'POST' });
      setCancelOpen(false);
      await load();
      onChanged?.();
    } catch (err) {
      setError(err?.message || 'Не удалось отменить запись');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <section className="screen active" id="screen-session">
        {loading ? (
          <div className="loader">Загрузка…</div>
        ) : error ? (
          <div className="empty-state" style={{ marginTop: 18 }}>
            <div className="empty-ico">⚠️</div>
            <h3>Ошибка</h3>
            <p>{error}</p>
          </div>
        ) : training ? (
          <>
            <div className="hero-image hero-image--media">
              <div className="hero-media">
                {activeMediaItem?.type === 'video' ? (
                  <video
                    ref={videoRef}
                    className="hero-media-video"
                    src={activeMediaItem.src}
                    autoPlay
                    muted
                    playsInline
                    loop
                    preload="metadata"
                    poster={mediaPosterUrl || undefined}
                    controls={false}
                  />
                ) : activeMediaItem?.type === 'image' ? (
                  <img
                    className="hero-media-image"
                    src={activeMediaItem.src}
                    alt={training?.title || 'Тренировка'}
                  />
                ) : (
                  <div className="hero-media-empty">
                    <span>Медиа недоступно</span>
                  </div>
                )}
              </div>

              <div className="hero-top">
                <button className="back-btn" type="button" onClick={onBack} aria-label="Назад">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>

                <button className="icon-btn" type="button" aria-label="Обновить" onClick={load}>
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M4 4v6h6M20 20v-6h-6" />
                    <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M20 8a8 8 0 0 0-14.8-3M4 16a8 8 0 0 0 14.8 3" />
                  </svg>
                </button>
              </div>

              <div className="hero-time-pill">{timePill}</div>

              <div className="hero-bottom-chips">
                {levelChips.map((lvl, i) => (
                  <span key={`${lvl}-${i}`} className="session-chip chip-level-light">
                    {lvl}
                  </span>
                ))}
              </div>
            </div>

            <div className="details-card details-card--intro">
              <div className="details-title">{training?.title || 'Тренировка'}</div>
              {training?.description ? (
                <div className="details-copy" style={{ marginTop: 10 }}>
                  {training.description}
                </div>
              ) : null}
              {tiers.length ? (
                <ul className="details-list">
                  {tiers.map((x) => (
                    <li key={x?.id ?? x?.title}>
                      {maybeFixUtf8Mojibake(x?.title)} — {Math.round(toNumber(x?.price) ?? 0)} ₽
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>

            <div className="details-card details-card--schedule">
              <div className="details-card-title">Дата и время</div>
              <div className="label-row">
                <span className="label-muted">Дата</span>
                <span className="label-strong">{dateLabel}</span>
              </div>
              <div className="label-row">
                <span className="label-muted">Время</span>
                <span className="label-strong">{timeRange}</span>
              </div>
              <div className="label-row">
                <span className="label-muted">Тренер</span>
                <span className="label-strong">{training?.coach_name || 'Без тренера'}</span>
              </div>
            </div>

            <div className="details-card details-card--price">
              <div className="details-card-title">Стоимость</div>
              <div className="label-row" style={{ marginBottom: 0 }}>
                <span className="label-muted">Стоимость</span>
                <span className="label-strong">{priceLabel || '—'}</span>
              </div>
            </div>

            <div className="details-card details-card--address">
              <div className="details-card-title">Адрес</div>
              <div className="label-row">
                <span className="label-muted">Адрес</span>
                <span className="label-strong">{locationLabel || 'Адрес уточняется'}</span>
              </div>

              {yandexMapSrc ? (
                <div className="map-embed" style={{ marginTop: 12 }}>
                  <div className="map-embed-frame">
                    <iframe
                      title="Yandex Map"
                      src={yandexMapSrc}
                      width="100%"
                      height="240"
                      frameBorder="0"
                      style={{ display: 'block' }}
                      loading="lazy"
                      referrerPolicy="no-referrer-when-downgrade"
                      allowFullScreen
                    />
                  </div>

                  {yandexRouteHref ? (
                    <div style={{ marginTop: 10 }}>
                      <button
                        className="primary-btn"
                        type="button"
                        onClick={() => openExternalLink(yandexRouteHref)}
                        style={{ width: '100%' }}
                      >
                        Построить маршрут
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="details-note" style={{ marginTop: 10 }}>
                  Карта появится, когда в API локаций/тренировок будут передаваться адрес или координаты.
                </p>
              )}
            </div>

            {adminNames.length ? (
              <div className="details-card details-card--admins">
                <div className="details-card-title">Администраторы</div>
                <div className="details-tags" role="list" aria-label="Администраторы">
                  {adminNames.map((name) => (
                    <span key={name} className="details-tag" role="listitem">
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="details-card details-card--cta">
              <button className="primary-btn" type="button" onClick={openEnrollFlow} disabled={enrollButtonDisabled}>
                {saving
                  ? 'Подождите…'
                  : checkingPayment
                    ? 'Проверяем оплату…'
                    : enrollButtonLabel}
              </button>

              {isEnrolled && calendarHref ? (
                <button
                  className="secondary-btn"
                  type="button"
                  onClick={() => openExternalLink(calendarHref)}
                  style={{ width: '100%', marginTop: 10 }}
                >
                  Добавить в календарь
                </button>
              ) : null}

              {isEnrolled ? (
                <p className="hint">{enrolledStatusLabel}</p>
              ) : (
                <p className="hint">
                  {participantsTotal > 0 ? `Уже записано: ${participantsTotal}` : 'Пока никто не записался — будьте первым!'}
                </p>
              )}
              {cancelBlockedHint ? (
                <p className="hint" style={{ color: 'var(--danger)' }}>
                  {cancelBlockedHint}
                </p>
              ) : null}
              {isTrainingFinished ? (
                <p className="hint" style={{ color: 'var(--danger)' }}>
                  Тренировка уже закончилась.
                </p>
              ) : null}
              {userHasActiveBan ? (
                <p className="hint" style={{ color: 'var(--danger)' }}>
                  У вас активный бан. Нажмите кнопку записи, чтобы посмотреть причину.
                </p>
              ) : null}
              {hasLevelBlock ? (
                <p className="hint" style={{ color: 'var(--danger)' }}>
                  {userLevelBlockReason}
                </p>
              ) : null}
              {pendingPaymentId ? (
                <p className="hint" style={{ color: 'var(--primary)' }}>
                  {paymentHint || 'У вас есть незавершенный платеж. Нажмите кнопку ниже, чтобы проверить статус.'}
                </p>
              ) : null}
            </div>

            <div className="participants-card">
              <div className="label-row">
                <span className="label-muted">Участники</span>
                <span className="participants-highlight">{freePlaces > 0 ? `Осталось ${freePlaces} мест` : 'Мест нет'}</span>
              </div>
              <div className="participants-row">
                <span>Минимум</span>
                <span>{peopleRange.min != null ? `${peopleRange.min} мест` : '—'}</span>
              </div>
              <div className="participants-row">
                <span>Максимум</span>
                <span>{peopleRange.max != null ? `${peopleRange.max} мест` : `${capacityMain} мест`}</span>
              </div>
              <div className="participants-row">
                <span>Свободно</span>
                <span>{freePlaces} мест</span>
              </div>
              {isAmpLuaTraining ? (
                <div className="participants-row">
                  <span>Резерв свободно</span>
                  <span>{reserveFreePlaces} мест</span>
                </div>
              ) : null}

              <div className="participants-list-block">
                <div className="participants-list-title">Основа ({participantsMain.length})</div>
                {participantsMain.length ? (
                  <ul className="participants-list">
                    {participantsMain.map((p, idx) => {
                      const meta = participantMeta(p, { isAmpLua: isAmpLuaTraining });
                      return (
                        <li key={`m-${p?.enrollment_id ?? p?.user_id ?? idx}`} className="participants-item">
                          <button
                            type="button"
                            className={`participants-item-btn ${p?.user_id ? 'clickable' : ''}`}
                            onClick={() => openParticipantProfile(p?.user_id)}
                            disabled={!p?.user_id}
                          >
                            <span className="participants-avatar">
                              <AvatarImage
                                src={resolveAvatarUrl(p?.avatar_url)}
                                alt={participantDisplayName(p)}
                                className="participants-avatar-image"
                                fallback={participantAvatarLetter(p)}
                              />
                            </span>
                            <span className="participants-user">
                              <span className="participants-name">{participantDisplayName(p)}</span>
                              {meta ? <span className="participants-meta">{meta}</span> : null}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <div className="participants-empty">Пока никто не записан в основу</div>
                )}
              </div>

              <div className="participants-list-block">
                <div className="participants-list-title">Резерв ({participantsReserve.length})</div>
                {participantsReserve.length ? (
                  <ul className="participants-list">
                    {participantsReserve.map((p, idx) => {
                      const meta = participantMeta(p, { isAmpLua: isAmpLuaTraining });
                      return (
                        <li key={`r-${p?.enrollment_id ?? p?.user_id ?? idx}`} className="participants-item">
                          <button
                            type="button"
                            className={`participants-item-btn ${p?.user_id ? 'clickable' : ''}`}
                            onClick={() => openParticipantProfile(p?.user_id)}
                            disabled={!p?.user_id}
                          >
                            <span className="participants-avatar">
                              <AvatarImage
                                src={resolveAvatarUrl(p?.avatar_url)}
                                alt={participantDisplayName(p)}
                                className="participants-avatar-image"
                                fallback={participantAvatarLetter(p)}
                              />
                            </span>
                            <span className="participants-user">
                              <span className="participants-name">{participantDisplayName(p)}</span>
                              {meta ? <span className="participants-meta">{meta}</span> : null}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <div className="participants-empty">В резерве пока никого</div>
                )}
              </div>

            </div>

            {additionalNotes ? (
              <div className="details-card details-card--extra">
                <div className="details-card-title">Дополнительно</div>
                <div className="details-copy">{additionalNotes}</div>
              </div>
            ) : null}
          </>
        ) : null}
      </section>

      {banInfoOpen ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <div className="modal-title">Запись недоступна</div>
            <div className="modal-body">
              <p>Ваш аккаунт находится в бане.</p>
              <p style={{ marginTop: 8 }}>
                Причина: <strong>{userBanReason || 'Причина не указана'}</strong>
              </p>
              <p style={{ marginTop: 8 }}>
                До: <strong>{userBanUntil ? userBanUntil.toLocaleString('ru-RU') : 'бессрочно'}</strong>
              </p>
            </div>
            <div className="modal-actions">
              <button className="primary-btn" type="button" onClick={() => setBanInfoOpen(false)}>
                Понятно
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {bookingOpen ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <div className="modal-title">Записаться на занятие</div>
            <div className="modal-body">
              <p>
                <strong>{training?.title || 'Тренировка'}</strong>
              </p>
              <p style={{ marginTop: 8 }}>
                {dateLabel ? `${dateLabel}, ` : ''}
                {timeRange}
              </p>
              <p style={{ marginTop: 10 }}>
                Стоимость: <strong>{priceLabel || '—'}</strong>
              </p>
              {canEnrollReserve && !canEnroll ? (
                <p className="hint" style={{ marginTop: 10 }}>
                  Основные места заняты. При записи вы попадёте в резерв.
                </p>
              ) : null}

              {bookingError && !isAmpLuaTraining ? (
                <div className="modal-warning" style={{ marginTop: 10, marginBottom: 0 }}>
                  <span>⚠️</span>
                  <span>{bookingError}</span>
                </div>
              ) : null}

              {isAmpLuaTraining ? (
                <div className="booking-position-step" style={{ marginTop: 14 }}>
                  <div className="details-card-title" style={{ marginBottom: 8 }}>
                    Выберите позицию
                  </div>

                  {bookingError ? (
                    <div className="modal-warning" style={{ marginBottom: 10 }}>
                      <span>⚠️</span>
                      <span>{bookingError}</span>
                    </div>
                  ) : null}

                  {bookingPositionOptions.length ? (
                    <div className="booking-position-groups">
                      {bookingPositionGroups.team1.length ? (
                        <div className="booking-position-team-block">
                          <div className="booking-position-team-title">Команда 1</div>
                          <div className="booking-position-list">
                            {bookingPositionGroups.team1.map((option) => renderBookingPositionOption(option))}
                          </div>
                        </div>
                      ) : null}

                      {bookingPositionGroups.team2.length ? (
                        <div className="booking-position-team-block">
                          <div className="booking-position-team-title">Команда 2</div>
                          <div className="booking-position-list">
                            {bookingPositionGroups.team2.map((option) => renderBookingPositionOption(option))}
                          </div>
                        </div>
                      ) : null}

                      {bookingPositionGroups.other.length ? (
                        <div className="booking-position-team-block">
                          <div className="booking-position-team-title">Другие позиции</div>
                          <div className="booking-position-list">
                            {bookingPositionGroups.other.map((option) => renderBookingPositionOption(option))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <p className="hint" style={{ textAlign: 'left', marginTop: 0 }}>
                      Сейчас нет свободных позиций для записи.
                    </p>
                  )}

                  {selectedBookingPosition ? (
                    <p className="hint" style={{ textAlign: 'left' }}>
                      Выбрано:{' '}
                      {buildPositionLabelWithTeam(
                        getBookingPositionTitle(selectedBookingPosition),
                        selectedBookingPosition?.teamLabel || '',
                      ) || selectedBookingPosition.displayLabel || selectedBookingPosition.label}
                    </p>
                  ) : bookingPositionOptions.length ? (
                    <p className="hint" style={{ textAlign: 'left' }}>
                      Выберите позицию и команду для продолжения.
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>

            <div className="modal-actions">
              <button className="secondary-btn" type="button" onClick={() => setBookingOpen(false)} disabled={saving}>
                Отмена
              </button>
              <button
                className="primary-btn"
                type="button"
                onClick={doEnroll}
                disabled={saving || (isAmpLuaTraining && (!bookingPositionOptions.length || !selectedBookingPosition))}
              >
                {'Перейти к оплате'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {cancelOpen ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <div className="modal-title">Отменить запись</div>
            <div className="modal-body">
              <p>Вы уверены, что хотите отменить запись?</p>
              <p className="hint" style={{ marginTop: 10 }}>
                Отмена доступна только до установленного времени перед началом тренировки.
              </p>
            </div>
            <div className="modal-actions">
              <button className="secondary-btn" type="button" onClick={() => setCancelOpen(false)} disabled={saving}>
                Назад
              </button>
              <button className="primary-btn" type="button" onClick={doCancel} disabled={saving}>
                Подтвердить
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {playerModalOpen ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={closeParticipantProfile}>
          <div className="modal" onClick={(ev) => ev.stopPropagation()}>
            <div className="modal-title">Профиль игрока</div>

            {playerModalLoading ? (
              <div className="modal-text" style={{ marginTop: 10 }}>
                Загрузка…
              </div>
            ) : null}

            {!playerModalLoading && playerModalError ? (
              <div className="modal-text" style={{ marginTop: 10, color: 'var(--danger)' }}>
                {playerModalError}
              </div>
            ) : null}

            {!playerModalLoading && !playerModalError && playerModalView ? (
              <>
                <div className="profile-card" style={{ marginTop: 12, cursor: 'default' }}>
                  <div className="profile-avatar">
                    <AvatarImage
                      src={playerModalView.avatarUrl}
                      alt={playerModalView.name}
                      className="profile-avatar-image"
                      fallback={playerModalView.avatarLetter}
                    />
                  </div>

                  <div className="profile-main">
                    <div className="profile-name">{playerModalView.name}</div>
                    <div className="profile-sub" style={{ marginTop: 6 }}>
                      Уровень: <b>{playerModalView.levelName}</b>
                    </div>

                    <div className="details-card" style={{ marginTop: 12 }}>
                      <div className="label-row">
                        <span className="label-muted">Рейтинг</span>
                        <span className="label-strong">{playerModalView.rating}</span>
                      </div>
                      <div className="label-row" style={{ marginBottom: 0 }}>
                        <span className="label-muted">Кубки</span>
                        <span className="label-strong">{playerModalView.cups}</span>
                      </div>
                    </div>

                    {playerModalView.telegram ? (
                      <div className="details-card" style={{ marginTop: 12 }}>
                        <div className="label-row" style={{ marginBottom: 0 }}>
                          <span className="label-muted">Telegram</span>
                          <span
                            className="label-strong"
                            style={{ color: 'var(--primary)', cursor: 'pointer' }}
                            onClick={() => openTelegramByUsername(playerModalView.telegramRaw)}
                          >
                            {playerModalView.telegram}
                          </span>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="modal-actions">
                  {playerModalView.telegram ? (
                    <button
                      className="primary-btn"
                      type="button"
                      onClick={() => openTelegramByUsername(playerModalView.telegramRaw)}
                    >
                      Перейти в Telegram
                    </button>
                  ) : null}
                  <button className="ghost-btn" type="button" onClick={closeParticipantProfile}>
                    Закрыть
                  </button>
                </div>
              </>
            ) : (
              <div className="modal-actions">
                <button className="ghost-btn" type="button" onClick={closeParticipantProfile}>
                  Закрыть
                </button>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}
