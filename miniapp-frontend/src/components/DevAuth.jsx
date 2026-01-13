// src/components/DevAuth.jsx
import { useState } from "react";
import { getDevAuth, setDevAuth } from "../auth";

export default function DevAuth({ onSaved }) {
  const current = getDevAuth();
  const [telegramId, setTelegramId] = useState(current.telegramId || "");
  const [userId, setUserId] = useState(current.userId || "");

  return (
    <div className="card">
      <div className="card-title">Dev-авторизация (для браузера)</div>
      <div className="muted" style={{ marginBottom: 10 }}>
        Уведомления в браузере требуют <b>X-Telegram-Id</b> или <b>X-User-Id</b>.
      </div>

      <label className="field">
        <div className="field-label">X-Telegram-Id</div>
        <input className="input" value={telegramId} onChange={(e) => setTelegramId(e.target.value)} placeholder="например 123456789" />
      </label>

      <label className="field">
        <div className="field-label">X-User-Id</div>
        <input className="input" value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="например 1" />
      </label>

      <button
        className="btn"
        onClick={() => {
          setDevAuth({ telegramId, userId });
          onSaved?.();
        }}
      >
        Сохранить
      </button>
    </div>
  );
}
