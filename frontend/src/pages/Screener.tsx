import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useRunScreen, useScreenStatus } from "../lib/api";
import { fmtUsd, VERDICT_META } from "../lib/format";
import type { ScreenResult } from "../lib/types";

type Filter = "setups" | "complete" | "watching" | "recentSetup" | "all";

const FILTERS: { key: Filter; label: string; tint?: string; pred: (r: ScreenResult) => boolean }[] = [
  { key: "setups", label: "Setups", pred: (r) => r.verdict !== "NO SETUP" },
  { key: "complete", label: "Complete", tint: "#1fdd97", pred: (r) => r.verdict === "COMPLETE SETUP" },
  { key: "watching", label: "Watching", tint: "#ffb020", pred: (r) => r.verdict === "WATCHING" },
  {
    key: "recentSetup",
    label: "Complete (1-6 wks ago)",
    tint: "#a855f7",
    pred: (r) => r.weeksSinceLastFull !== null && r.weeksSinceLastFull >= 1 && r.weeksSinceLastFull <= 6,
  },
  { key: "all", label: "All", pred: () => true },
];

export function Screener() {
  const [universe, setUniverse] = useState<string>("sp500");
  const { data } = useScreenStatus(universe);
  const run = useRunScreen();
  const [filter, setFilter] = useState<Filter>("setups");

  const state = data?.state ?? "idle";

  // Automatically start the scan if we select a universe that has no cached data
  useEffect(() => {
    if (data && data.state === "idle" && !run.isPending) {
      run.mutate({ universe, force: true });
    }
  }, [data?.state, universe]);
  const running = state === "running";
  const activeUniverse = data?.universe;
  const total = data?.total ?? 0;
  const done = data?.done ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  const results = data?.results ?? [];
  const complete = results.filter((r) => r.verdict === "COMPLETE SETUP").length;
  const watching = results.filter((r) => r.verdict === "WATCHING").length;
  const recent = results.filter(
    (r) => r.weeksSinceLastFull !== null && r.weeksSinceLastFull >= 1 && r.weeksSinceLastFull <= 6
  ).length;

  const counts = useMemo(
    () => Object.fromEntries(FILTERS.map((f) => [f.key, results.filter(f.pred).length])),
    [results],
  );

  const rows = useMemo(() => {
    const active = FILTERS.find((f) => f.key === filter) ?? FILTERS[4];
    const filtered = results.filter(active.pred);
    if (filter === "recentSetup") {
      return filtered.sort((a, b) => {
        const aWatching = a.verdict === "WATCHING" ? 1 : 0;
        const bWatching = b.verdict === "WATCHING" ? 1 : 0;
        if (aWatching !== bWatching) {
          return bWatching - aWatching; // 1 (watching) comes first
        }
        const aWeeks = a.weeksSinceLastFull ?? 999;
        const bWeeks = b.weeksSinceLastFull ?? 999;
        return aWeeks - bWeeks; // ascending weeks since setup
      });
    }
    return filtered.sort((a, b) => b.score - a.score || (b.mansfieldRs ?? -99) - (a.mansfieldRs ?? -99));
  }, [results, filter]);

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight">
            <span className="text-gradient">Auto-Screener</span>
          </h1>
          <p className="mt-1.5 max-w-xl text-sm text-muted">
            Scans index constituents through the Holy Grail engine and ranks every hit by
            weighted score. Data is weekly and cached hourly.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select 
            value={universe} 
            onChange={(e) => setUniverse(e.target.value)}
            className="rounded-xl border border-line bg-surface px-3 py-1.5 text-sm text-ink outline-none focus:border-violet"
          >
            <option value="sp500">S&P 500</option>
            <option value="russell1000">Russell 1000</option>
            <option value="russell2000">Russell 2000</option>
          </select>
          <button
            onClick={() => run.mutate({ universe, force: true })}
            disabled={run.isPending || running}
            className="btn-primary whitespace-nowrap disabled:opacity-60"
          >
            {running && activeUniverse === universe ? `Scanning… ${pct}%` : "Manual Refresh"}
          </button>
        </div>
      </div>

      {running && (
        <div className="card p-4">
          <div className="mb-2 flex items-center justify-between text-xs text-muted">
            <span>
              Scanning {done} / {total} tickers…
            </span>
            <span className="tnum">{data?.found ?? 0} hits so far</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
            <div
              className="h-full rounded-full bg-gradient-to-r from-violet to-cyan transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {state === "error" && (
        <div className="card border-bear/30 bg-bear/5 p-4 text-sm text-bear">
          Scan failed: {data?.error ?? "unknown error"}
        </div>
      )}

      {results.length > 0 && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex gap-3">
              <MiniStat label="Scanned" value={String(done)} active={filter === "all"} onClick={() => setFilter("all")} />
              <MiniStat label="Complete" value={String(complete)} tint="#1fdd97" active={filter === "complete"} onClick={() => setFilter("complete")} />
              <MiniStat label="Watching" value={String(watching)} tint="#ffb020" active={filter === "watching"} onClick={() => setFilter("watching")} />
              <MiniStat label="Complete (1-6 w)" value={String(recent)} tint="#a855f7" active={filter === "recentSetup"} onClick={() => setFilter("recentSetup")} />
            </div>
            <div className="flex flex-wrap rounded-2xl border border-line bg-white/[0.02] p-1 text-sm">
              {FILTERS.map((f) => {
                const active = filter === f.key;
                return (
                  <button
                    key={f.key}
                    onClick={() => setFilter(f.key)}
                    className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 font-medium transition ${
                      active ? "bg-white/[0.08] text-ink" : "text-muted hover:text-ink"
                    }`}
                  >
                    {f.tint && (
                      <span className="h-2 w-2 rounded-full" style={{ background: f.tint }} />
                    )}
                    {f.label}
                    <span className="tnum text-xs text-faint">{counts[f.key]}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {rows.length === 0 ? (
            <div className="card p-6 text-sm text-muted">
              No qualifying setups in this scan. Switch to “All” to see every scored ticker.
            </div>
          ) : (
            <ResultsTable rows={rows} />
          )}
        </>
      )}

      {state === "idle" && results.length === 0 && (
        <div className="card grid place-items-center gap-3 p-12 text-center">
          <div className="text-4xl">🛰️</div>
          <div className="text-sm text-muted">
            The {universe} index hasn't been scanned recently. Click Manual Refresh to start a sweep.
          </div>
        </div>
      )}
    </div>
  );
}

function MiniStat({
  label,
  value,
  tint,
  active,
  onClick,
}: {
  label: string;
  value: string;
  tint?: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-2xl border px-4 py-2.5 text-center transition ${
        active ? "border-line-strong bg-white/[0.08]" : "border-line bg-white/[0.03] hover:bg-white/[0.05]"
      }`}
    >
      <div className="tnum font-display text-lg font-bold" style={tint ? { color: tint } : undefined}>
        {value}
      </div>
      <div className="text-[11px] text-faint">{label}</div>
    </button>
  );
}

function ResultsTable({ rows }: { rows: ScreenResult[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line-strong text-left text-[11px] uppercase tracking-wider text-faint">
              <th className="px-4 py-3 font-semibold">Ticker</th>
              <th className="px-4 py-3 font-semibold">Score</th>
              <th className="px-4 py-3 font-semibold">Verdict</th>
              <th className="px-4 py-3 font-semibold">Entry Zone</th>
              <th className="px-4 py-3 font-semibold">Last Close</th>
              <th className="px-4 py-3 font-semibold">Mansfield RS</th>
              <th className="px-4 py-3 font-semibold">RSI</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const meta = VERDICT_META[r.verdict] ?? VERDICT_META["NO SETUP"];
              const scorePct = Math.round(r.score * 100);
              return (
                <tr key={r.ticker} className="border-b border-line/50 transition hover:bg-white/[0.02]">
                  <td className="px-4 py-3">
                    <Link
                      to={`/scanner?ticker=${r.ticker}`}
                      className="rounded-md border border-info/20 bg-info/10 px-2 py-1 font-bold text-info transition hover:bg-info/20"
                    >
                      {r.ticker}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/[0.06]">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${scorePct}%`, background: meta.hex }}
                        />
                      </div>
                      <span className="tnum text-xs text-muted">{scorePct}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="rounded-md border px-2.5 py-1 text-xs font-bold"
                      style={{ color: meta.hex, borderColor: `${meta.hex}40`, background: "rgba(255,255,255,0.03)" }}
                    >
                      {meta.emoji} {meta.label}
                    </span>
                    {r.weeksSinceLastFull !== null && r.weeksSinceLastFull > 0 && (
                      <span className="text-[10px] text-faint block mt-1">
                        Setup: {r.weeksSinceLastFull} wk{r.weeksSinceLastFull > 1 ? "s" : ""} ago
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 tnum text-muted">
                    {r.entryLow === null || r.entryHigh === null
                      ? "N/A"
                      : `${fmtUsd(r.entryLow)} – ${fmtUsd(r.entryHigh)}`}
                  </td>
                  <td className="px-4 py-3 tnum">{fmtUsd(r.lastClose)}</td>
                  <td
                    className={`px-4 py-3 tnum font-semibold ${
                      (r.mansfieldRs ?? 0) >= 0 ? "text-bull" : "text-bear"
                    }`}
                  >
                    {r.mansfieldRs === null ? "N/A" : r.mansfieldRs.toFixed(3)}
                  </td>
                  <td className="px-4 py-3 tnum text-muted">
                    {r.rsi14 === null ? "N/A" : r.rsi14.toFixed(1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
