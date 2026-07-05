import { useEffect, useRef, useState } from "react";
import { useSettings, isDefault, type Settings } from "../lib/settings";

interface Field {
  key: keyof Settings;
  label: string;
  step?: number;
}

const GROUPS: { title: string; fields: Field[] }[] = [
  {
    title: "EMA / MA",
    fields: [
      { key: "ema_fast", label: "EMA Fast" },
      { key: "ema_mid", label: "EMA Mid" },
      { key: "ema_slow", label: "EMA Slow" },
      { key: "ma50w", label: "50-Week MA" },
    ],
  },
  {
    title: "Rules",
    fields: [
      { key: "rsi_len", label: "RSI Length" },
      { key: "vol_mult", label: "Vol Multiplier", step: 0.1 },
      { key: "vol_lookbk", label: "Vol Lookback" },
      { key: "retest_max", label: "Max % Above 50WMA", step: 0.5 },
      { key: "base_min", label: "Min Base (wks)" },
    ],
  },
  {
    title: "Weights & Thresholds",
    fields: [
      { key: "w1", label: "W1 Retest", step: 0.05 },
      { key: "w2", label: "W2 Breakout", step: 0.05 },
      { key: "w3", label: "W3 Base", step: 0.05 },
      { key: "w4", label: "W4 Green Cloud", step: 0.05 },
      { key: "w5", label: "W5 Mansfield RS", step: 0.05 },
      { key: "w6", label: "W6 RSI>50", step: 0.05 },
      { key: "partial_thresh", label: "Partial Threshold", step: 0.05 },
      { key: "full_thresh", label: "Full Threshold", step: 0.05 },
    ],
  },
];

export function SettingsPopover() {
  const { settings, showCloud, setSetting, setShowCloud, reset } = useSettings();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const modified = !isDefault(settings);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative grid h-9 w-9 place-items-center rounded-xl border border-line bg-white/[0.03] text-muted transition hover:text-ink"
        title="Settings & thresholds"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
          <path d="M19.14 12.94a7.49 7.49 0 000-1.88l2.03-1.58a.5.5 0 00.12-.64l-1.92-3.32a.5.5 0 00-.61-.22l-2.39.96a7.3 7.3 0 00-1.62-.94l-.36-2.54a.5.5 0 00-.5-.42h-3.84a.5.5 0 00-.5.42l-.36 2.54c-.58.24-1.12.56-1.62.94l-2.39-.96a.5.5 0 00-.61.22L2.68 8.84a.5.5 0 00.12.64l2.03 1.58a7.49 7.49 0 000 1.88l-2.03 1.58a.5.5 0 00-.12.64l1.92 3.32c.14.24.42.34.68.22l2.39-.96c.5.38 1.04.7 1.62.94l.36 2.54c.04.24.25.42.5.42h3.84c.25 0 .46-.18.5-.42l.36-2.54c.58-.24 1.12-.56 1.62-.94l2.39.96c.26.12.54.02.68-.22l1.92-3.32a.5.5 0 00-.12-.64l-2.06-1.58zM12 15.5A3.5 3.5 0 1112 8.5a3.5 3.5 0 010 7z" />
        </svg>
        {modified && <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-brand" />}
      </button>

      {open && (
        <div className="absolute right-0 top-11 z-40 w-[300px] animate-fade-up rounded-2xl border border-line bg-surface-2/95 p-4 shadow-card backdrop-blur-xl">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm font-semibold">Settings & Thresholds</span>
            <button onClick={reset} className="text-xs text-brand hover:underline">
              Reset
            </button>
          </div>

          <label className="mb-3 flex cursor-pointer items-center justify-between rounded-lg border border-line bg-white/[0.02] px-3 py-2">
            <span className="text-sm">Show EMA cloud</span>
            <input
              type="checkbox"
              checked={showCloud}
              onChange={(e) => setShowCloud(e.target.checked)}
              className="h-4 w-4 accent-brand"
            />
          </label>

          <div className="max-h-[46vh] space-y-3 overflow-y-auto pr-1">
            {GROUPS.map((g) => (
              <div key={g.title}>
                <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-faint">
                  {g.title}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {g.fields.map((f) => (
                    <label key={f.key} className="text-xs text-muted">
                      <span className="mb-1 block truncate">{f.label}</span>
                      <input
                        type="number"
                        step={f.step ?? 1}
                        value={settings[f.key]}
                        onChange={(e) => setSetting(f.key, Number(e.target.value))}
                        className="w-full rounded-lg border border-line bg-white/[0.03] px-2 py-1.5 text-sm text-ink outline-none focus:border-brand/60"
                      />
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
