import React, { useEffect, useState } from "react";
import { AppStoreProvider, useAppStore } from "./state/appStore";
import { telegramReadyExpand } from "./lib/telegram";
import { tryTelegramAuth } from "./lib/api";
import { HomeScreen } from "./screens/HomeScreen";
import { FiltersScreen } from "./screens/FiltersScreen";

type Screen = "home" | "filters";

function AppInner() {
  const store = useAppStore();
  const [screen, setScreen] = useState<Screen>("home");

  useEffect(() => {
    telegramReadyExpand();
  }, []);

  useEffect(() => {
    // Этап 12.1: токен
    (async () => {
      if (store.token) return;
      const token = await tryTelegramAuth();
      if (token) store.setToken(token);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (screen === "filters") {
    return (
      <FiltersScreen
        onBack={() => setScreen("home")}
        onApply={() => setScreen("home")}
      />
    );
  }

  return <HomeScreen onOpenFilters={() => setScreen("filters")} />;
}

export default function App() {
  return (
    <AppStoreProvider>
      <AppInner />
    </AppStoreProvider>
  );
}
