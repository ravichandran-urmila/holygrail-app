import { useMemo, useState } from "react";
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
  const globalState = (data as any)?.globalState ?? "idle";
  const activeUniverse = (data as any)?.activeUniverse;
  const globalRunning = globalState === "running";
  const done = data?.done ?? 0;

  const _jobState = (data as any)?.jobState ?? "idle";
  const jobDone = (data as any)?.jobDone ?? 0;
  const jobTotal = (data as any)?.jobTotal ?? 0;
  const completedCount = data?.completedUniverses?.length ?? 0;
  const activeProgress = jobTotal > 0 ? jobDone / jobTotal : 0;
  const overallPct = Math.min(100, Math.round(((completedCount + (globalRunning ? activeProgress : 0)) / 3) * 100));


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
        </div>
      </div>

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
            The {universe} index hasn't been scanned recently. Click Trigger Manual Override below to start a sweep.
          </div>
        </div>
      )}

      {/* Manual Override & Progress Section at the Bottom */}
      <div className="mt-12 rounded-3xl border border-line bg-gradient-to-br from-white/[0.03] to-white/[0.01] p-6 shadow-xl backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="space-y-1">
            <h3 className="font-display text-lg font-bold tracking-tight text-ink">
              System Manual Override Scan
            </h3>
            <p className="text-xs text-muted max-w-xl">
              Triggers a sequential Holy Grail indicator scan across all three index universes (S&P 500, Russell 1000, Russell 2000). To avoid API rate limiting, a delay is enforced between each index.
            </p>
          </div>
          <div>
            <button
              onClick={() => run.mutate({ force: true })}
              disabled={run.isPending || globalRunning}
              className="btn-primary flex items-center gap-2 px-5 py-2.5 font-semibold transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
            >
              {globalRunning ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Scan in Progress
                </>
              ) : (
                "Trigger Manual Override"
              )}
            </button>
          </div>
        </div>

        {globalRunning && (
          <div className="mt-6 border-t border-line/40 pt-6 space-y-5 animate-fade-in">
            {/* Index Checklist / Status Grid */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {[
                { key: "sp500", label: "S&P 500 Index" },
                { key: "russell1000", label: "Russell 1000 Index" },
                { key: "russell2000", label: "Russell 2000 Index" },
              ].map((item) => {
                const completed = data?.completedUniverses?.includes(item.key) ?? false;
                const isScanning = activeUniverse === item.key && _jobState === "running";
                
                let statusColor = "text-faint border-line bg-white/[0.01]";
                let statusLabel = "Pending";
                let pulseDot = false;
                
                if (completed) {
                  statusColor = "text-[#1fdd97] border-[#1fdd97]/20 bg-[#1fdd97]/5";
                  statusLabel = "Completed";
                } else if (isScanning) {
                  statusColor = "text-violet border-violet/30 bg-violet/5";
                  statusLabel = `Scanning (${jobDone}/${jobTotal})`;
                  pulseDot = true;
                }
                
                return (
                  <div
                    key={item.key}
                    className={`flex items-center justify-between rounded-2xl border p-4 transition duration-300 ${statusColor}`}
                  >
                    <div className="space-y-0.5">
                      <div className="font-semibold text-sm">{item.label}</div>
                      <div className="text-[11px] font-medium opacity-80">{statusLabel}</div>
                    </div>
                    {completed ? (
                      <span className="text-lg">✅</span>
                    ) : pulseDot ? (
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-violet"></span>
                      </span>
                    ) : (
                      <span className="h-2 w-2 rounded-full bg-white/20" />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Overall Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-muted">
                <span>Overall Sequence Progress</span>
                <span className="tnum font-bold text-violet">{overallPct}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-white/[0.04] border border-line/30 p-[2px]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-violet via-[#ff4081] to-[#1fdd97] transition-all duration-500 ease-out"
                  style={{ width: `${overallPct}%` }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
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
