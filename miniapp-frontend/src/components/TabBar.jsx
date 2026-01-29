import React from 'react';

const TABS = [
  { key: 'home', label: 'Главная', iconPath: "M4 11l8-7 8 7v7a2 2 0 0 1-2 2h-4V13H10v7H6a2 2 0 0 1-2-2v-7z" },
  { key: 'rating', label: 'Рейтинг', iconPath: "M8 21l4-4 4 4M12 3v14" },
  { key: 'notifications', label: 'Уведомления', iconPath: "M15 17h5l-1.5-2M4 17h11M12 5a4 4 0 0 1 4 4v2.5l1 2.5H7l1-2.5V9a4 4 0 0 1 4-4zM10 19a2 2 0 0 0 4 0" },
  { key: 'more', label: 'Ещё', iconPath: "M5 6h14M5 12h14M5 18h14" },
];

export default function TabBar({ active, onChange }) {
  return (
    <nav className="tabbar">
      {TABS.map((t) => (
        <button
          key={t.key}
          className={`tab-btn ${active === t.key ? 'active' : ''}`}
          onClick={() => onChange?.(t.key)}
        >
          <div className="tab-btn-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d={t.iconPath} />
            </svg>
          </div>
          <span>{t.label}</span>
        </button>
      ))}
    </nav>
  );
}