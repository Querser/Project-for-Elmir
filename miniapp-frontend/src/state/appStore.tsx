import React, { createContext, useContext, useMemo, useState } from "react";
import type { FiltersState, LocationOption, Training } from "../types";

type AppState = {
  token: string;
  setToken: (v: string) => void;

  city: string;
  setCity: (v: string) => void;

  selectedDate: Date;
  setSelectedDate: (d: Date) => void;

  filters: FiltersState;
  setFilters: (f: FiltersState) => void;

  trainings: Training[];
  setTrainings: (t: Training[]) => void;

  locationOptions: LocationOption[];
  setLocationOptions: (v: LocationOption[]) => void;
};

const Ctx = createContext<AppState | null>(null);

function initFilters(): FiltersState {
  return {
    type: new Set<string>(),
    level: new Set<string>(),
    location: new Set<string>(),
  };
}

export function AppStoreProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string>(localStorage.getItem("access_token") || "");
  const [city, setCity] = useState<string>("Москва");
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [filters, setFilters] = useState<FiltersState>(initFilters());
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [locationOptions, setLocationOptions] = useState<LocationOption[]>([]);

  const value = useMemo<AppState>(() => ({
    token,
    setToken: (v) => {
      setToken(v);
      if (v) localStorage.setItem("access_token", v);
      else localStorage.removeItem("access_token");
    },
    city,
    setCity,
    selectedDate,
    setSelectedDate,
    filters,
    setFilters,
    trainings,
    setTrainings,
    locationOptions,
    setLocationOptions,
  }), [token, city, selectedDate, filters, trainings, locationOptions]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppStore(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAppStore must be used within AppStoreProvider");
  return v;
}
