import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export interface Settings {
  ema_fast: number;
  ema_mid: number;
  ema_slow: number;
  ma50w: number;
  rsi_len: number;
  vol_mult: number;
  vol_lookbk: number;
  retest_max: number;
  base_min: number;
  w1: number;
  w2: number;
  w3: number;
  w4: number;
  w5: number;
  w6: number;
  partial_thresh: number;
  full_thresh: number;
}

export const DEFAULT_SETTINGS: Settings = {
  ema_fast: 5,
  ema_mid: 9,
  ema_slow: 21,
  ma50w: 50,
  rsi_len: 14,
  vol_mult: 1.5,
  vol_lookbk: 10,
  retest_max: 15.0,
  base_min: 15,
  w1: 0.15,
  w2: 0.1,
  w3: 0.1,
  w4: 0.25,
  w5: 0.3,
  w6: 0.1,
  partial_thresh: 0.35,
  full_thresh: 0.7,
};

interface SettingsCtx {
  settings: Settings;
  showCloud: boolean;
  setSetting: (key: keyof Settings, value: number) => void;
  setShowCloud: (v: boolean) => void;
  reset: () => void;
}

const Ctx = createContext<SettingsCtx | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [showCloud, setShowCloud] = useState(true);

  const value = useMemo<SettingsCtx>(
    () => ({
      settings,
      showCloud,
      setSetting: (key, v) => setSettings((s) => ({ ...s, [key]: v })),
      setShowCloud,
      reset: () => setSettings(DEFAULT_SETTINGS),
    }),
    [settings, showCloud],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSettings(): SettingsCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSettings must be used within SettingsProvider");
  return ctx;
}

export function settingsToQuery(s: Settings): string {
  return Object.entries(s)
    .map(([k, v]) => `${k}=${v}`)
    .join("&");
}

export function isDefault(s: Settings): boolean {
  return (Object.keys(DEFAULT_SETTINGS) as (keyof Settings)[]).every(
    (k) => s[k] === DEFAULT_SETTINGS[k],
  );
}
