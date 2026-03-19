import React, { useEffect, useMemo, useState } from 'react';

import './App.css';
import TabBar from './components/TabBar';

import { initTelegramAuth } from './auth';

import Schedule from './screens/Schedule';
import Rating from './screens/Rating';
import Notifications from './screens/Notifications';
import More from './screens/More';

import Filters from './screens/Filters';
import TrainingDetail from './screens/TrainingDetail';
import Profile from './screens/Profile';

/**
 * Tabs keys match the keys in TabBar.jsx
 */
const TAB_SCHEDULE = 'home';
const TAB_RATING = 'rating';
const TAB_NOTIFICATIONS = 'notifications';
const TAB_MORE = 'more';

const LS_THEME = 'ui.theme';

function expandTelegramWebApp(tg) {
  if (!tg) return;
  try {
    tg.ready?.();
  } catch {
    // ignore
  }
  try {
    tg.expand?.();
  } catch {
    // ignore
  }
  try {
    if (typeof tg.requestFullscreen === 'function') {
      tg.requestFullscreen();
    }
  } catch {
    // ignore
  }
}

function readTrainingIdFromUrl() {
  if (typeof window === 'undefined') return null;
  try {
    const url = new URL(window.location.href);
    const raw = url.searchParams.get('training_id');
    if (!raw) return null;
    const value = Number(raw);
    return Number.isFinite(value) && value > 0 ? value : null;
  } catch {
    return null;
  }
}

function clearPaymentQueryParams() {
  if (typeof window === 'undefined') return;
  try {
    const url = new URL(window.location.href);
    if (!url.searchParams.has('training_id') && !url.searchParams.has('payment_result')) return;
    url.searchParams.delete('training_id');
    url.searchParams.delete('payment_result');
    window.history.replaceState(null, '', url.toString());
  } catch {
    // ignore
  }
}

function updateViewportHeightVar() {
  if (typeof window === 'undefined') return;
  const viewportHeight = window.visualViewport?.height || window.innerHeight;
  if (!viewportHeight) return;
  document.documentElement.style.setProperty('--app-height', `${Math.round(viewportHeight)}px`);
}

function updateSafeTopVar(tg) {
  if (typeof document === 'undefined') return;

  const tgTopInsetCandidates = [
    tg?.safeAreaInset?.top,
    tg?.contentSafeAreaInset?.top,
    tg?.viewportSafeAreaInset?.top,
  ];
  const tgTopInset = tgTopInsetCandidates
    .map((value) => Number(value))
    .find((value) => Number.isFinite(value) && value >= 0);

  if (tgTopInset != null) {
    document.documentElement.style.setProperty('--safe-top-inset', `${Math.round(tgTopInset)}px`);
  }
}

export default function App() {
  const tg = useMemo(() => {
    return typeof window !== 'undefined' ? window.Telegram?.WebApp : null;
  }, []);

  const initialTrainingId = useMemo(() => readTrainingIdFromUrl(), []);

  const [activeTab, setActiveTab] = useState(TAB_SCHEDULE);

  const [filters, setFilters] = useState({
    locationIds: [],
    coachNames: [],
    levelNames: [],
    kinds: [],
    types: [],
    startTimeFrom: '',
    startTimeTo: '',
  });

  const [isDark, setIsDark] = useState(() => {
    try {
      return (localStorage.getItem(LS_THEME) || 'light') === 'dark';
    } catch {
      return false;
    }
  });

  // refreshTick — чтобы пере-загружать расписание после записи/отмены
  const [refreshTick, setRefreshTick] = useState(0);

  // Полноэкранные оверлеи поверх табов (filters/training/profile)
  const [overlay, setOverlay] = useState(() =>
    initialTrainingId
      ? { type: 'training', payload: { trainingId: initialTrainingId } }
      : { type: null, payload: null },
  );

  useEffect(() => {
    initTelegramAuth().catch(() => {
      // в dev-режимах / без Telegram это нормально
    });
  }, []);

  useEffect(() => {
    if (!initialTrainingId) return;
    clearPaymentQueryParams();
  }, [initialTrainingId]);

  useEffect(() => {
    try {
      document.body.classList.toggle('theme-dark', Boolean(isDark));
    } catch {
      // ignore
    }
  }, [isDark]);

  useEffect(() => {
    try {
      localStorage.setItem(LS_THEME, isDark ? 'dark' : 'light');
    } catch {
      // ignore
    }
  }, [isDark]);

  useEffect(() => {
    if (!tg) return;
    expandTelegramWebApp(tg);
    try {
      tg.setHeaderColor?.(isDark ? '#0b1220' : '#f4f7fc');
      tg.setBackgroundColor?.(isDark ? '#0b1220' : '#f4f7fc');
    } catch {
      // ignore
    }
  }, [tg, isDark, activeTab, overlay.type]);

  useEffect(() => {
    updateViewportHeightVar();
    updateSafeTopVar(tg);

    const onResize = () => {
      updateViewportHeightVar();
      updateSafeTopVar(tg);
    };
    window.addEventListener('resize', onResize, { passive: true });
    window.addEventListener('orientationchange', onResize, { passive: true });
    window.visualViewport?.addEventListener?.('resize', onResize, { passive: true });
    window.visualViewport?.addEventListener?.('scroll', onResize, { passive: true });

    return () => {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('orientationchange', onResize);
      window.visualViewport?.removeEventListener?.('resize', onResize);
      window.visualViewport?.removeEventListener?.('scroll', onResize);
    };
  }, [tg]);

  useEffect(() => {
    const hasOverlay = Boolean(overlay.type);
    document.body.classList.toggle('overlay-open', hasOverlay);
    return () => {
      document.body.classList.remove('overlay-open');
    };
  }, [overlay.type]);

  const openTraining = (trainingId) => {
    if (!trainingId) return;
    setOverlay({ type: 'training', payload: { trainingId } });
  };

  const openFilters = () => setOverlay({ type: 'filters', payload: null });
  const openProfile = () => setOverlay({ type: 'profile', payload: null });
  const closeOverlay = () => setOverlay({ type: null, payload: null });

  const bumpRefresh = () => setRefreshTick((x) => x + 1);

  // ВАЖНО: это “страховка”, если где-то в App.css/других стилях остались сломанные правила
  // (left:50% / transform / max-width). Inline победит любой css.
  const overlayStyleFix = {
    left: 0,
    right: 0,
    transform: 'none',
    maxWidth: 'none',
  };

  return (
    <div className="app" id="app">
      <div className="screen-container">
        {activeTab === TAB_SCHEDULE && (
          <div className="screen active" id="screen-home">
            <Schedule
              filters={filters}
              refreshTick={refreshTick}
              onOpenFilters={openFilters}
              onOpenTraining={openTraining}
            />
          </div>
        )}

        {activeTab === TAB_RATING && (
          <div className="screen active" id="screen-rating">
            <Rating />
          </div>
        )}

        {activeTab === TAB_NOTIFICATIONS && (
          <div className="screen active" id="screen-notifications">
            <Notifications />
          </div>
        )}

        {activeTab === TAB_MORE && (
          <div className="screen active" id="screen-more">
            <More
              darkMode={isDark}
              onToggleDarkMode={(checked) => setIsDark(Boolean(checked))}
              onOpenProfile={openProfile}
            />
          </div>
        )}
      </div>

      <TabBar active={activeTab} onChange={setActiveTab} />

      {overlay.type === 'filters' ? (
        <div className="overlay-screen" style={overlayStyleFix}>
          <div className="overlay-content">
            <Filters
              initialFilters={filters}
              onApply={(next) => {
                setFilters(next);
                closeOverlay();
              }}
              onBack={closeOverlay}
            />
          </div>
        </div>
      ) : null}

      {overlay.type === 'training' ? (
        <div className="overlay-screen" style={overlayStyleFix}>
          <div className="overlay-content">
            <TrainingDetail
              trainingId={overlay.payload?.trainingId}
              onBack={closeOverlay}
              onChanged={() => bumpRefresh()}
            />
          </div>
        </div>
      ) : null}

      {overlay.type === 'profile' ? (
        <div className="overlay-screen" style={overlayStyleFix}>
          <div className="overlay-content">
            <Profile onBack={closeOverlay} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
