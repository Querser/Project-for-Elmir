// src/components/Topbar.jsx
export default function Topbar({ title, onBack, right }) {
  return (
    <div className="topbar">
      <button className="topbar-back" onClick={onBack} style={{ visibility: onBack ? "visible" : "hidden" }}>
        ←
      </button>
      <h1 className="topbar-title">{title}</h1>
      <div className="topbar-right">{right || <span />}</div>
    </div>
  );
}
