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
    if (/[А-Яа-яЁё]/.test(decoded)) return decoded;
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

export default function TrainingDetail({ trainingId, onBack, onChanged }) {
  const [training, setTraining] = useState(null);
  const [locationLabel, setLocationLabel] = useState('');
  const [locationObj, setLocationObj] = useState(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [bookingOpen, setBookingOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);

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

  const yandexMapSrc = useMemo(() => {
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
  }, [coords, mapTextLabel]);

  const yandexRouteHref = useMemo(() => {
    if (coords.lat != null && coords.lon != null) {
      return `https://yandex.ru/maps/?mode=routes&rtext=~${coords.lat},${coords.lon}&rtt=auto`;
    }
    if (mapTextLabel) {
      return `https://yandex.ru/maps/?mode=routes&rtext=~${encodeURIComponent(mapTextLabel)}&rtt=auto`;
    }
    return '';
  }, [coords, mapTextLabel]);

  const enrollButtonLabel = useMemo(() => {
    if (isEnrolled) return 'Отменить запись';
    if (canEnroll) return 'Записаться';
    if (canEnrollReserve && isReserveAvailable) return 'Записаться в резерв';
    return 'Запись недоступна';
  }, [isEnrolled, canEnroll, canEnrollReserve, isReserveAvailable]);

  const enrollButtonDisabled = useMemo(() => {
    if (loading || saving) return true;
    if (isEnrolled) return !canCancel;
    if (canEnroll) return false;
    if (canEnrollReserve && isReserveAvailable) return false;
    return true;
  }, [loading, saving, isEnrolled, canCancel, canEnroll, canEnrollReserve, isReserveAvailable]);

  const priceLabel = useMemo(() => {
    const p = training?.final_price ?? training?.price;
    const n = toNumber(p);
    if (n == null) return '';
    return `${Math.round(n)} ₽`;
  }, [training]);

  const openEnrollFlow = () => {
    if (isEnrolled) {
      if (!canCancel) return;
      setCancelOpen(true);
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

      const payload = {
        training_id: trainingId,
        is_paid: false,
      };

      const tierId = training?.picked_price_tier_id ?? null;
      if (tierId != null) payload.price_tier_id = tierId;

      await apiFetch('/api/v1/enrollments', {
        method: 'POST',
        body: payload,
      });

      setBookingOpen(false);
      await load();
      onChanged?.();
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

                <button className="icon-btn" type="button" aria-label="Статус" disabled>
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M18 8l-6 6-3-3" />
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
              {isEnrolled ? <p className="hint">{enrolledStatusLabel}</p> : <p className="hint">Успей записаться первым!</p>}
              {cancelBlockedHint ? (
                <p className="hint" style={{ color: 'var(--danger)' }}>
                  {cancelBlockedHint}
                </p>
              ) : null}
            </div>

            <button className="primary-btn" type="button" onClick={openEnrollFlow} disabled={enrollButtonDisabled}>
              {saving ? 'Подождите…' : enrollButtonLabel}
            </button>
          </>
        ) : null}
      </section>

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
                Записаться
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
                По ТЗ отмена возможна не позднее, чем за 2 часа до начала.
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
    </>
  );
}