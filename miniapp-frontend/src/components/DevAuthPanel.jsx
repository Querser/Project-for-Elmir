import { useMemo, useState } from "react";
import { clearAuth, getDevAuth, isInTelegram, setDevAuth } from "../auth";

/**
 * DEV-only панель авторизации (для проверки в браузере).
 * В Telegram она автоматически скрыта.
 *
 * Бэкенд текущего проекта (на момент этапов 12.1–12.2) умеет авторизовывать
 * запросы через заголовки X-Telegram-Id / X-User-Id.
 */
export default function DevAuthPanel() {
  const visible = useMemo(() => !isInTelegram(), []);
  const initial = useMemo(() => getDevAuth(), []);

  const [telegramId, setTelegramId] = useState(initial.telegramId || "");
  const [userId, setUserId] = useState(initial.userId || "");
  const [note, setNote] = useState("");

  if (!visible) return null;

  const onSave = () => {
    const t = telegramId.trim();
    const u = userId.trim();

    if (!t) {
      setNote("Укажи Telegram ID (число). Например: 123456789");
      return;
    }

    setDevAuth({ telegramId: t, userId: u || "" });
    setNote("Сохранено. Перезагружаю страницу…");
    window.location.reload();
  };

  const onClear = () => {
    clearAuth();
    setNote("Очищено. Перезагружаю страницу…");
    window.location.reload();
  };

  return (
    <div className="dev-auth">
      <div className="dev-auth__title">DEV auth (только браузер)</div>

      <div className="dev-auth__row">
        <label className="dev-auth__label">Telegram ID</label>
        <input
          className="dev-auth__input"
          value={telegramId}
          onChange={(e) => setTelegramId(e.target.value)}
          placeholder="Например: 123456789"
          inputMode="numeric"
        />
      </div>

      <div className="dev-auth__row">
        <label className="dev-auth__label">User ID (необязательно)</label>
        <input
          className="dev-auth__input"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="Например: 1"
          inputMode="numeric"
        />
      </div>

      <div className="dev-auth__actions">
        <button className="dev-auth__btn" onClick={onSave}>
          Сохранить
        </button>
        <button className="dev-auth__btn dev-auth__btn--ghost" onClick={onClear}>
          Очистить
        </button>
      </div>

      {note ? <div className="dev-auth__note">{note}</div> : null}

      <div className="dev-auth__hint">
        Подсказка: Telegram ID — это числовой ID пользователя (tgUser.id). В Telegram Mini App он
        подставляется автоматически, а панель скрывается.
      </div>
    </div>
  );
}
