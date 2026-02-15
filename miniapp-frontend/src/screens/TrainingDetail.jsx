import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api';

/**
 * Иногда бек отдает UTF-8 байты, но они уже превращены в строку как Latin-1,
 * поэтому в JS приходит "Ð¢ÐµÑ..." вместо "Тре...".
 * Эта функция пытается восстановить нормальный UTF-8.
 */
function maybeFixUtf8Mojibake(value) {
  if (value == null) return '';
  const s = typeof value === 'string' || typeof value === 'number' ? String(value) : '';
  if (!s) return '';
  // эвристика: типичные символы кракозябр
  if (!/[ÐÑ]/.test(s)) return s;

  try {
    const bytes = new Uint8Array([...s].map((ch) => ch.charCodeAt(0)));
    const decoded = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
    // если после декода появилась кириллица — значит стало лучше
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

function participantMeta(item) {
  const parts = [];
  const rawUsername = maybeFixUtf8Mojibake(item?.username ?? '').toString().trim();
  if (rawUsername) {
    parts.push(rawUsername.startsWith('@') ? rawUsername : `@${rawUsername}`);
  }

  const levelName = maybeFixUtf8Mojibake(item?.level_name ?? '').toString().trim();
  if (levelName) parts.push(levelName);

  return parts.join(' • ');
}

function participantAvatarLetter(item) {
  const name = participantDisplayName(item).replace(/^@/, '').trim();
  return name ? name[0].toUpperCase() : '•';
}

function resolveAvatarUrl(raw) {
  const value = maybeFixUtf8Mojibake(raw ?? '').toString().trim();
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  try {
    return new URL(value, window.location.origin).toString();
  } catch {
    return value;
  }
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

  const openExternalLink = (url) => {
    if (!url) return;
    const tg = window?.Telegram?.WebApp;
    if (tg?.openLink) {
      try {
        tg.openLink(url);
        return;
      } catch {
        // fallback ниже
      }
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const fetchLocationById = async (locId) => {
    // ВАЖНО: у тебя НЕТ /api/v1/locations/{id}, поэтому работаем только со списками.
    // Но сейчас списки возвращают лишь {id}, без name/address/coords — это ограничение бэка/БД.
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

      // Чиним потенциальные кракозябры на ключевых текстах
      const t = {
        ...tRaw,
        title: maybeFixUtf8Mojibake(tRaw?.title),
        description: maybeFixUtf8Mojibake(tRaw?.description),
        coach_name: maybeFixUtf8Mojibake(tRaw?.coach_name),
      };

      let locLabel = '';
      let locObj = null;

      // 1) Пытаемся достать адрес/название из тренировки (если бек начнет это отдавать)
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
        t?.location, // может быть строкой или объектом
        t?.place, // может быть строкой или объектом
      ]);

      // 2) Если location/place объектом — сохраняем
      const directLoc = t?.location ?? t?.place ?? null;
      if (directLoc) {
        const directLabel = normalizeLocationLabel(directLoc);
        if (directLabel) locLabel = directLabel;
        if (typeof directLoc === 'object') locObj = directLoc;
      }

      // 3) Если есть location_id — пробуем найти в списке
      const locId = t?.location_id ?? t?.locationId ?? null;
      if (locId != null) {
        const found = await fetchLocationById(locId);
        if (found) {
          // сейчас found = {id}, но если позже бек начнет отдавать поля — тут автоматически заработает
          const lbl = normalizeLocationLabel(found);
          if (lbl) locLabel = lbl;
          locObj = found;
        }

        // Если вообще ничего нет — показываем юзер-френдли подпись (но НЕ используем её для карты)
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

  const freePlaces = useMemo(() => {
    const fp = toNumber(training?.free_places);
    if (fp != null) return fp;
    const occupied = toNumber(training?.occupied_main) ?? 0;
    const left = capacityMain - occupied;
    return left >= 0 ? left : 0;
  }, [training, capacityMain]);

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

  // НЕ пытаемся строить карту по заглушке "Локация #1"
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
      setBookingOpen(true);
    }
  };

  const doEnroll = async () => {
    if (!trainingId) return;
    try {
      setSaving(true);
      setError('');
      setPaymentHint('');

      const payload = {
        training_id: trainingId,
      };

      const tierId = training?.picked_price_tier_id ?? null;
      if (tierId != null) payload.price_tier_id = tierId;

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
      setError(err?.message || 'Не удалось записаться');
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

  const img =
    training?.image_url ||
    'https://images.unsplash.com/photo-1521412644187-c49fa049e84d?auto=format&fit=crop&w=1200&q=60';

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
            <div className="hero-image" style={{ backgroundImage: `url(${img})` }}>
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

            <div className="details-card">
              <div className="details-title">{training?.title || 'Тренировка'}</div>
              {training?.description ? (
                <p className="details-note" style={{ marginTop: 10 }}>
                  {training.description}
                </p>
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

            <div className="details-card">
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
              <div className="label-row">
                <span className="label-muted">Стоимость</span>
                <span className="label-strong">{priceLabel || '—'}</span>
              </div>
              <div className="label-row">
                <span className="label-muted">Адрес</span>
                <span className="label-strong">{locationLabel || 'Адрес уточняется'}</span>
              </div>

              {/* Yandex Map Widget */}
              {yandexMapSrc ? (
                <div style={{ marginTop: 12 }}>
                  <div style={{ borderRadius: 16, overflow: 'hidden' }}>
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
              ) : null}

              {!yandexMapSrc ? (
                <p className="details-note" style={{ marginTop: 10 }}>
                  Карта появится, когда в API локаций/тренировок будут передаваться адрес или координаты (сейчас в БД
                  locations только id).
                </p>
              ) : null}

              <p className="details-note">
                Точное количество участников и финальная стоимость рассчитываются перед началом тренировки.
              </p>
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

              <div className="participants-list-block">
                <div className="participants-list-title">Основа ({participantsMain.length})</div>
                {participantsMain.length ? (
                  <ul className="participants-list">
                    {participantsMain.map((p, idx) => (
                      <li key={`m-${p?.enrollment_id ?? p?.user_id ?? idx}`} className="participants-item">
                        <button
                          type="button"
                          className={`participants-item-btn ${p?.user_id ? 'clickable' : ''}`}
                          onClick={() => openParticipantProfile(p?.user_id)}
                          disabled={!p?.user_id}
                        >
                          <span className="participants-avatar">
                            {resolveAvatarUrl(p?.avatar_url) ? (
                              <img
                                src={resolveAvatarUrl(p?.avatar_url)}
                                alt={participantDisplayName(p)}
                                className="participants-avatar-image"
                              />
                            ) : (
                              participantAvatarLetter(p)
                            )}
                          </span>
                          <span className="participants-user">
                            <span className="participants-name">{participantDisplayName(p)}</span>
                            {participantMeta(p) ? <span className="participants-meta">{participantMeta(p)}</span> : null}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="participants-empty">Пока никто не записан в основу</div>
                )}
              </div>

              <div className="participants-list-block">
                <div className="participants-list-title">Резерв ({participantsReserve.length})</div>
                {participantsReserve.length ? (
                  <ul className="participants-list">
                    {participantsReserve.map((p, idx) => (
                      <li key={`r-${p?.enrollment_id ?? p?.user_id ?? idx}`} className="participants-item">
                        <button
                          type="button"
                          className={`participants-item-btn ${p?.user_id ? 'clickable' : ''}`}
                          onClick={() => openParticipantProfile(p?.user_id)}
                          disabled={!p?.user_id}
                        >
                          <span className="participants-avatar">
                            {resolveAvatarUrl(p?.avatar_url) ? (
                              <img
                                src={resolveAvatarUrl(p?.avatar_url)}
                                alt={participantDisplayName(p)}
                                className="participants-avatar-image"
                              />
                            ) : (
                              participantAvatarLetter(p)
                            )}
                          </span>
                          <span className="participants-user">
                            <span className="participants-name">{participantDisplayName(p)}</span>
                            {participantMeta(p) ? <span className="participants-meta">{participantMeta(p)}</span> : null}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="participants-empty">В резерве пока никого</div>
                )}
              </div>

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

            <button className="primary-btn" type="button" onClick={openEnrollFlow} disabled={enrollButtonDisabled}>
              {saving
                ? '\u041f\u043e\u0434\u043e\u0436\u0434\u0438\u0442\u0435\u2026'
                : checkingPayment
                  ? '\u041f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u043c \u043e\u043f\u043b\u0430\u0442\u0443\u2026'
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
            </div>

            <div className="modal-actions">
              <button className="secondary-btn" type="button" onClick={() => setBookingOpen(false)} disabled={saving}>
                Отмена
              </button>
              <button className="primary-btn" type="button" onClick={doEnroll} disabled={saving}>
                {'\u041f\u0435\u0440\u0435\u0439\u0442\u0438 \u043a \u043e\u043f\u043b\u0430\u0442\u0435'}
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
                    {playerModalView.avatarUrl ? (
                      <img
                        src={playerModalView.avatarUrl}
                        alt={playerModalView.name}
                        className="profile-avatar-image"
                      />
                    ) : (
                      playerModalView.avatarLetter
                    )}
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
