import { useEffect, useRef, useState } from "react";
import { useWatchlist } from "../lib/api";
import type { WatchlistItem } from "../lib/types";

function playChime() {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    const beep = (freq: number, at: number, dur: number) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.setValueAtTime(freq, ctx.currentTime + at);
      gain.gain.setValueAtTime(0.14, ctx.currentTime + at);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + at + dur);
      osc.start(ctx.currentTime + at);
      osc.stop(ctx.currentTime + at + dur);
    };
    beep(659.25, 0, 0.3);
    beep(880.0, 0.12, 0.4);
  } catch {
    /* audio blocked */
  }
}

export function AlertBell() {
  const [enabled, setEnabled] = useState(() => localStorage.getItem("hg_alerts_enabled") === "true");
  const [toast, setToast] = useState<string | null>(null);
  const { data } = useWatchlist();
  const seen = useRef<Map<string, string> | null>(null);

  useEffect(() => {
    if (!data?.items) return;
    const snapshot = new Map<string, string>(
      data.items.map((i: WatchlistItem) => [i.ticker, `${i.verdict}:${i.priceAdded}`]),
    );
    if (seen.current === null) {
      seen.current = snapshot;
      return;
    }
    if (!enabled) {
      seen.current = snapshot;
      return;
    }
    const changed: WatchlistItem[] = [];
    for (const item of data.items) {
      const prev = seen.current.get(item.ticker);
      if (prev === undefined || prev !== `${item.verdict}:${item.priceAdded}`) changed.push(item);
    }
    seen.current = snapshot;
    if (changed.length > 0) {
      const c = changed[0];
      playChime();
      setToast(`${c.ticker} → ${c.verdict} at $${c.priceAdded.toFixed(2)}`);
      if ("Notification" in window && Notification.permission === "granted") {
        new Notification("Expert Corner updated", {
          body: `${c.ticker} updated to ${c.verdict} at $${c.priceAdded.toFixed(2)}`,
        });
      }
      setTimeout(() => setToast(null), 6000);
    }
  }, [data, enabled]);

  const toggle = () => {
    const next = !enabled;
    setEnabled(next);
    localStorage.setItem("hg_alerts_enabled", String(next));
    if (next) {
      playChime();
      if ("Notification" in window) Notification.requestPermission();
    }
  };

  return (
    <>
      <button
        onClick={toggle}
        title={enabled ? "Alerts on" : "Alerts off"}
        className={`grid h-9 w-9 place-items-center rounded-xl border transition ${
          enabled
            ? "border-bull/40 bg-bull/10 text-bull"
            : "border-line bg-white/[0.03] text-muted hover:text-ink"
        }`}
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
          <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
        </svg>
      </button>
      {toast && (
        <div className="fixed bottom-5 right-5 z-50 animate-fade-up rounded-xl border border-brand/40 bg-surface-2/95 px-4 py-3 text-sm shadow-glow backdrop-blur-xl">
          <span className="mr-2">⚡</span>
          {toast}
        </div>
      )}
    </>
  );
}
