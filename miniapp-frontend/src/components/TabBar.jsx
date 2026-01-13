// src/components/Tabbar.jsx
export default function Tabbar({ tab, setTab }) {
  return (
    <nav className="tabbar">
      <button className={`tabbtn ${tab === "schedule" ? "active" : ""}`} onClick={() => setTab("schedule")}>
        Главная
      </button>
      <button className={`tabbtn ${tab === "rating" ? "active" : ""}`} onClick={() => setTab("rating")}>
        Рейтинг
      </button>
      <button
        className={`tabbtn ${tab === "profile" ? "active" : ""}`}
        onClick={() => setTab("profile")}
      >
        Профиль
      </button>
      <button
        className={`tabbtn ${tab === "notifications" ? "active" : ""}`}
        onClick={() => setTab("notifications")}
      >
        Уведомления
      </button>
      <button className={`tabbtn ${tab === "more" ? "active" : ""}`} onClick={() => setTab("more")}>
        Ещё
      </button>
    </nav>
  );
}
