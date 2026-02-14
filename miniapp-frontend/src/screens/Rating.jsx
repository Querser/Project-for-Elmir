import React, { useEffect, useMemo, useState } from "react";
import { apiFetch, extractItems } from "../api";
import RefreshButton from "../components/RefreshButton";

// Уровни строго по ТЗ
const LEVEL_TABS = [
  { key: "novice", label: "Новичок", emoji: "🥉" },
  { key: "mid_minus", label: "Средний-", emoji: "🥈" },
  { key: "mid", label: "Средний", emoji: "🥇", hasHint: true },
  { key: "mid_plus", label: "Средний+", emoji: "🏆", hasHint: true },
];

function normalizeStr(v) {
  if (v === null || v === undefined) return "";
  return String(v).trim();
}

// Маппинг на случай, если в БД старые названия
function normalizeLevelToKey(nameRaw) {
  const n = normalizeStr(nameRaw).toLowerCase().replace(/\s+/g, "");
  if (!n) return "novice";

  // новые
  if (n.includes("нович")) return "novice";
  if (n.includes("средний-") || n.includes("средний−")) return "mid_minus";
  if (n === "средний") return "mid";
  if (n.includes("средний+")) return "mid_plus";

  // старые (примерные)
  if (n.includes("лайтпро") || n.includes("lightpro") || n.includes("pro")) return "mid_plus";
  if (n.includes("лайт+") || n.includes("light+")) return "mid";
  if (n.includes("лайт") || n.includes("light")) return "mid_minus";
  if (n.includes("медиум") || n.includes("medium")) return "mid_plus";

  return "mid";
}

function normalizeLevelLabel(nameRaw) {
  const n = normalizeStr(nameRaw).toLowerCase().replace(/\s+/g, "");
  if (!n) return "Новичок";
  if (n.includes("нович")) return "Новичок";
  if (n.includes("средний-") || n.includes("средний−")) return "Средний-";
  if (n === "средний") return "Средний";
  if (n.includes("средний+")) return "Средний+";
  return "—";
}

function pickPlayerName(p) {
  const fn = normalizeStr(p?.first_name ?? p?.firstName ?? "");
  const ln = normalizeStr(p?.last_name ?? p?.lastName ?? "");
  const full = `${fn} ${ln}`.trim();
  if (full) return full;
  return normalizeStr(p?.username ?? p?.tg_username ?? p?.login ?? "Игрок");
}

function pickAvatarLetter(name) {
  const s = normalizeStr(name);
  return s ? s[0].toUpperCase() : "•";
}

function pickScore(item) {
  return (
    item?.points ??
    item?.score ??
    item?.rating_points ??
    item?.rating ??
    item?.value ??
    0
  );
}

function pickCups(item) {
  return item?.cups ?? item?.cup ?? item?.trophies ?? 0;
}

function pickLevelNameFromItem(item, levelsById) {
  const id = item?.level_id ?? item?.levelId ?? item?.player_level_id ?? null;
  if (id !== null && id !== undefined) {
    const fromMap = levelsById.get(Number(id));
    if (fromMap) return fromMap;
  }
  const direct =
    item?.level_name ??
    item?.levelName ??
    item?.level ??
    item?.player_level ??
    item?.player_level_name ??
    null;

  return normalizeStr(direct);
}

function tgUsernamePretty(username) {
  const u = normalizeStr(username);
  if (!u) return "";
  return `@${u.replace(/^@/, "")}`;
}

function openTelegram(username) {
  const u = normalizeStr(username).replace(/^@/, "");
  if (!u) return;

  const url = `https://t.me/${u}`;

  try {
    const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : null;
    if (tg?.openTelegramLink) tg.openTelegramLink(url);
    else if (tg?.openLink) tg.openLink(url);
    else window.open(url, "_blank", "noopener,noreferrer");
  } catch {
    try {
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      // ignore
    }
  }
}

export default function Rating() {
  const [activeTab, setActiveTab] = useState("novice");
  const [loading, setLoading] = useState(true);
  const [errorText, setErrorText] = useState("");

  const [levelsById, setLevelsById] = useState(new Map());
  const [ratings, setRatings] = useState([]);
  const [me, setMe] = useState(null);

  const [hintTabKey, setHintTabKey] = useState(null);

  // Модалка профиля игрока
  const [playerModalOpen, setPlayerModalOpen] = useState(false);
  const [playerModalUserId, setPlayerModalUserId] = useState(null);
  const [playerModalLoading, setPlayerModalLoading] = useState(false);
  const [playerModalError, setPlayerModalError] = useState("");
  const [playerModalProfile, setPlayerModalProfile] = useState(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    let alive = true;

    async function load() {
      setLoading(true);
      setErrorText("");

      try {
        const levelsRes = await apiFetch(`/api/v1/levels`);
        const levels = extractItems(levelsRes) || [];
        const map = new Map();
        for (const l of levels) {
          const id = l?.id ?? l?.level_id ?? null;
          const name = normalizeStr(l?.name ?? l?.title ?? "");
          if (id !== null) map.set(Number(id), name);
        }

        const rRes = await apiFetch(`/api/v1/ratings?limit=200&offset=0`);
        const rItems = extractItems(rRes) || [];

        const meRes = await apiFetch(`/api/v1/ratings/me`);
        const meObj = meRes?.item ?? meRes ?? null;

        if (!alive) return;
        setLevelsById(map);
        setRatings(rItems);
        setMe(meObj);
      } catch (e) {
        if (!alive) return;
        setErrorText(e?.message || "Ошибка загрузки рейтинга");
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();

    return () => {
      alive = false;
    };
  }, [reloadTick]);

  const prepared = useMemo(() => {
    return (ratings || []).map((it, idx) => {
      const player = it?.player ?? it?.user ?? it?.profile ?? it ?? {};
      const name = pickPlayerName(player);
      const score = pickScore(it);
      const levelName =
        pickLevelNameFromItem(it, levelsById) ||
        pickLevelNameFromItem(player, levelsById);

      const levelKey = normalizeLevelToKey(levelName);

      return {
        raw: it,
        player,
        id: player?.id ?? it?.player_id ?? it?.user_id ?? it?.id ?? idx,
        name,
        avatarLetter: pickAvatarLetter(name),
        score: Number(score) || 0,
        cups: Number(pickCups(it)) || 0,
        levelName: normalizeStr(levelName),
        levelKey,
      };
    });
  }, [ratings, levelsById]);

  // ВАЖНО: place считаем ВНУТРИ уровня (как на референсах)
  const filtered = useMemo(() => {
    const list = prepared.filter((p) => p.levelKey === activeTab);
    list.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      if (b.cups !== a.cups) return b.cups - a.cups;
      return String(a.id).localeCompare(String(b.id));
    });
    return list.map((x, i) => ({ ...x, place: i + 1 }));
  }, [prepared, activeTab]);

  const meView = useMemo(() => {
    if (!me) return null;

    const score = pickScore(me);
    const cups = pickCups(me);

    const levelName = pickLevelNameFromItem(me, levelsById);
    const levelKey = normalizeLevelToKey(levelName);
    const tabLabel = LEVEL_TABS.find((t) => t.key === levelKey)?.label || "—";

    return {
      score: Number(score) || 0,
      cups: Number(cups) || 0,
      levelLabel: tabLabel,
      position: me?.position ?? null,
      totalUsers: me?.total_users ?? me?.total ?? null,
    };
  }, [me, levelsById]);

  const hintText = useMemo(() => {
    if (!hintTabKey) return "";
    if (hintTabKey === "mid") {
      return "Средний: игроки с устойчивым уровнем игры, стабильно держат приём/подачу, понимают базовые взаимодействия.";
    }
    if (hintTabKey === "mid_plus") {
      return "Средний+: более высокий темп, уверенная техника и принятие решений. Чаще играют на результат, меньше ошибок.";
    }
    return "";
  }, [hintTabKey]);

  function openPlayerModal(userId) {
    if (!userId) return;
    setPlayerModalUserId(Number(userId));
    setPlayerModalOpen(true);
    setPlayerModalLoading(true);
    setPlayerModalError("");
    setPlayerModalProfile(null);
  }

  function closePlayerModal() {
    setPlayerModalOpen(false);
    setPlayerModalUserId(null);
    setPlayerModalLoading(false);
    setPlayerModalError("");
    setPlayerModalProfile(null);
  }

  useEffect(() => {
    let alive = true;

    async function loadPublicProfile() {
      if (!playerModalOpen || !playerModalUserId) return;

      try {
        setPlayerModalLoading(true);
        setPlayerModalError("");

        const res = await apiFetch(`/api/v1/profile/${playerModalUserId}`);
        const prof = res?.item ?? res ?? null;

        if (!alive) return;
        setPlayerModalProfile(prof);
      } catch (e) {
        if (!alive) return;
        setPlayerModalError(e?.message || "Не удалось загрузить профиль игрока");
      } finally {
        if (alive) setPlayerModalLoading(false);
      }
    }

    loadPublicProfile();

    return () => {
      alive = false;
    };
  }, [playerModalOpen, playerModalUserId]);

  const playerModalView = useMemo(() => {
    if (!playerModalProfile) return null;

    const name = pickPlayerName(playerModalProfile);
    const avatarLetter = pickAvatarLetter(name);

    const lvlRaw =
      playerModalProfile?.level_name ||
      levelsById.get(Number(playerModalProfile?.level_id)) ||
      "";
    const levelLabel = normalizeLevelLabel(lvlRaw);

    const rating = Number(playerModalProfile?.rating ?? 0) || 0;
    const cups = Number(playerModalProfile?.cups ?? 0) || 0;

    const username = normalizeStr(playerModalProfile?.username || "");
    const telegram = tgUsernamePretty(username);

    return {
      name,
      avatarLetter,
      levelLabel,
      rating,
      cups,
      telegram,
      telegramUsernameRaw: username,
    };
  }, [playerModalProfile, levelsById]);

  return (
    <div className="screen active">
      <div className="topbar">
        <h1 className="topbar-title">Рейтинг</h1>
        <RefreshButton onClick={() => setReloadTick((prev) => prev + 1)} />
      </div>

      <div className="rating-tabs">
        {LEVEL_TABS.map((t) => (
          <div
            key={t.key}
            className={`rating-tab ${t.key === activeTab ? "active" : ""}`}
            onClick={() => setActiveTab(t.key)}
            role="button"
            tabIndex={0}
          >
            <div className="rating-tab-icon">
              <span style={{ fontSize: 16 }}>{t.emoji}</span>
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span>{t.label}</span>
              {t.hasHint ? (
                <button
                  className="linklike"
                  style={{ fontSize: 12, fontWeight: 900 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setHintTabKey(t.key);
                  }}
                  title="Подробнее"
                >
                  ?
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {loading ? <div className="loader">Загрузка…</div> : null}

      {!loading && errorText ? (
        <div className="empty-state">
          <span className="empty-ico">⚠️</span>
          Ошибка
          <div style={{ marginTop: 6 }}>{errorText}</div>
        </div>
      ) : null}

      {!loading && !errorText && meView ? (
        <div className="details-card">
          <div className="label-row">
            <span className="label-muted">Мой уровень</span>
            <span className="label-strong">{meView.levelLabel}</span>
          </div>
          <div className="label-row">
            <span className="label-muted">Мои очки</span>
            <span className="label-strong" style={{ color: "var(--primary)" }}>
              {meView.score}
            </span>
          </div>
          <div className="label-row">
            <span className="label-muted">Мои кубки</span>
            <span className="label-strong">{meView.cups}</span>
          </div>
          {meView.position ? (
            <div className="label-row" style={{ marginBottom: 0 }}>
              <span className="label-muted">Моё место</span>
              <span className="label-strong">
                {meView.position}
                {meView.totalUsers ? ` / ${meView.totalUsers}` : ""}
              </span>
            </div>
          ) : (
            <div className="label-row" style={{ marginBottom: 0 }}>
              <span className="label-muted">Моё место</span>
              <span className="label-strong">—</span>
            </div>
          )}
        </div>
      ) : null}

      {!loading && !errorText && filtered.length === 0 ? (
        <div className="empty-state">
          <span className="empty-ico">🏐</span>
          В этом разделе пока нет игроков
        </div>
      ) : null}

      {!loading && !errorText && filtered.length > 0 ? (
        <div className="content">
          {filtered.map((p) => (
            <div
              key={p.id}
              className="player-card"
              role="button"
              tabIndex={0}
              onClick={() => openPlayerModal(p.id)}
            >
              <div className="player-place">{p.place}</div>
              <div className="player-avatar">{p.avatarLetter}</div>
              <div className="player-main">
                <div className="player-name">{p.name}</div>
                <div className="player-score">
                  <svg viewBox="0 0 24 24">
                    <path
                      d="M12 3l2.5 6.5L21 10l-5 4 1.5 7L12 18l-5.5 3 1.5-7-5-4 6.5-.5L12 3z"
                      strokeWidth="2"
                      strokeLinejoin="round"
                    />
                  </svg>
                  {p.score}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {hintTabKey ? (
        <div className="modal-backdrop" onClick={() => setHintTabKey(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">Подробнее</div>
            <div className="modal-text">{hintText}</div>
            <div className="modal-actions">
              <button className="primary-btn" onClick={() => setHintTabKey(null)}>
                Понятно
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {playerModalOpen ? (
        <div className="modal-backdrop" onClick={closePlayerModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">Профиль игрока</div>

            {playerModalLoading ? (
              <div className="modal-text" style={{ marginTop: 10 }}>
                Загрузка…
              </div>
            ) : null}

            {!playerModalLoading && playerModalError ? (
              <div className="modal-text" style={{ marginTop: 10, color: "var(--danger)" }}>
                {playerModalError}
              </div>
            ) : null}

            {!playerModalLoading && !playerModalError && playerModalView ? (
              <>
                <div className="profile-card" style={{ marginTop: 12, cursor: "default" }}>
                  <div className="profile-avatar">{playerModalView.avatarLetter}</div>

                  <div className="profile-main">
                    <div className="profile-name">{playerModalView.name}</div>

                    <div className="profile-sub" style={{ marginTop: 6 }}>
                      Уровень: <b>{playerModalView.levelLabel}</b>
                    </div>

                    <div className="details-card" style={{ marginTop: 12 }}>
                      <div className="label-row">
                        <span className="label-muted">Рейтинг</span>
                        <span className="label-strong">{playerModalView.rating}</span>
                      </div>
                      <div className="label-row" style={{ marginBottom: 0 }}>
                        <span className="label-muted">Кубки</span>
                        <span className="label-strong">{playerModalView.cups}</span>
                      </div>
                    </div>

                    {playerModalView.telegram ? (
                      <div className="details-card" style={{ marginTop: 12 }}>
                        <div className="label-row" style={{ marginBottom: 0 }}>
                          <span className="label-muted">Telegram</span>
                          <span
                            className="label-strong"
                            style={{ color: "var(--primary)", cursor: "pointer" }}
                            onClick={() => openTelegram(playerModalView.telegramUsernameRaw)}
                            title="Открыть Telegram"
                          >
                            {playerModalView.telegram}
                          </span>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="modal-actions">
                  {playerModalView.telegram ? (
                    <button
                      className="primary-btn"
                      onClick={() => openTelegram(playerModalView.telegramUsernameRaw)}
                    >
                      Перейти в Telegram
                    </button>
                  ) : null}
                  <button className="ghost-btn" onClick={closePlayerModal}>
                    Закрыть
                  </button>
                </div>
              </>
            ) : (
              <div className="modal-actions">
                <button className="ghost-btn" onClick={closePlayerModal}>
                  Закрыть
                </button>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
