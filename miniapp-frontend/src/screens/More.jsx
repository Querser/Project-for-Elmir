// src/screens/More.jsx
import { useEffect, useState } from "react";
import { clearAuth } from "../auth";

const LS_THEME = "ui.theme"; // light|dark

export default function More() {
  const [page, setPage] = useState("menu");
  const [theme, setTheme] = useState(localStorage.getItem(LS_THEME) || "light");

  useEffect(() => {
    document.body.classList.toggle("theme-dark", theme === "dark");
    localStorage.setItem(LS_THEME, theme);
  }, [theme]);

  function logout() {
    clearAuth();
    window.location.reload();
  }

  if (page === "promo") {
    return (
      <section className="screen">
        <div className="card">
          <div className="card-title">Акции</div>
          <div className="muted">Статичная страница. Текст добавим по ТЗ.</div>
          <button className="btn btn-ghost" onClick={() => setPage("menu")} style={{ marginTop: 12 }}>
            Назад
          </button>
        </div>
      </section>
    );
  }

  if (page === "rules") {
    return (
      <section className="screen">
        <div className="card">
          <div className="card-title">Правила</div>
          <div className="muted">Статичная страница. Текст добавим по ТЗ.</div>
          <button className="btn btn-ghost" onClick={() => setPage("menu")} style={{ marginTop: 12 }}>
            Назад
          </button>
        </div>
      </section>
    );
  }

  if (page === "contacts") {
    return (
      <section className="screen">
        <div className="card">
          <div className="card-title">Контакты</div>
          <div className="muted">Статичная страница. Текст добавим по ТЗ.</div>
          <button className="btn btn-ghost" onClick={() => setPage("menu")} style={{ marginTop: 12 }}>
            Назад
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="screen">
      <div className="card">
        <div className="card-title">Ещё</div>

        <button className="btn btn-ghost" onClick={() => setPage("promo")}>Акции</button>
        <button className="btn btn-ghost" onClick={() => setPage("rules")}>Правила</button>
        <button className="btn btn-ghost" onClick={() => setPage("contacts")}>Контакты</button>

        <div style={{ height: 12 }} />

        <label className="field field-row">
          <input type="checkbox" checked={theme === "dark"} onChange={(e) => setTheme(e.target.checked ? "dark" : "light")} />
          <span>Тёмная тема</span>
        </label>

        <div style={{ height: 12 }} />

        <button className="btn btn-red" onClick={logout}>Выйти</button>
      </div>
    </section>
  );
}
