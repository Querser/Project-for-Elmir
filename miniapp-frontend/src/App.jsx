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

export default function App() {
  const tg = useMemo(() => {
    return typeof window !== 'undefined' ? window.Telegram?.WebApp : null;
  }, []);

  const [activeTab, setActiveTab] = useState(TAB_SCHEDULE);

  const [filters, setFilters] = useState({
    locationIds: [],
    coachNames: [],
    levelNames: [],
    kinds: [],
    types: [],
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
  const [overlay, setOverlay] = useState({ type: null, payload: null });

  useEffect(() => {
    initTelegramAuth().catch(() => {
      // в dev-режимах / без Telegram это нормально
    });
  }, []);

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
    try {
      tg.ready?.();
      tg.expand?.();
      tg.setHeaderColor?.(isDark ? '#0b1220' : '#f4f7fc');
      tg.setBackgroundColor?.(isDark ? '#0b1220' : '#f4f7fc');
    } catch {
      // ignore
    }
  }, [tg, isDark]);

  const openTraining = (trainingId) => {
    if (!trainingId) return;
    setOverlay({ type: 'training', payload: { trainingId } });
  };

  const openFilters = () => setOverlay({ type: 'filters', payload: null });
  const openProfile = () => setOverlay({ type: 'profile', payload: null });
  const closeOverlay = () => setOverlay({ type: null, payload: null });

  const bumpRefresh = () => setRefreshTick((x) => x + 1);

  return (
    <div className="app">
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
        <div className="overlay-screen">
          <Filters
            initialFilters={filters}
            onApply={(next) => {
              setFilters(next);
              closeOverlay();
            }}
            onBack={closeOverlay}
          />
        </div>
      ) : null}

      {overlay.type === 'training' ? (
        <div className="overlay-screen">
          <TrainingDetail
            trainingId={overlay.payload?.trainingId}
            onBack={closeOverlay}
            onChanged={() => bumpRefresh()}
          />
        </div>
      ) : null}

      {overlay.type === 'profile' ? (
        <div className="overlay-screen">
          <Profile onBack={closeOverlay} />
        </div>
      ) : null}
    </div>
  );
}