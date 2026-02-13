import React from 'react';

export default function RefreshButton({ onClick, disabled = false, ariaLabel = 'Обновить' }) {
  return (
    <button
      className="icon-btn refresh-btn"
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      title={ariaLabel}
    >
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M4 4v6h6M20 20v-6h-6" />
        <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M20 8a8 8 0 0 0-14.8-3M4 16a8 8 0 0 0 14.8 3" />
      </svg>
    </button>
  );
}
