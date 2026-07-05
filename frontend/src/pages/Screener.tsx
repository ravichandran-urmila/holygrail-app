import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useRunScreen, useScreenStatus } from "../lib/api";
import { fmtUsd, VERDICT_META } from "../lib/format";
import type { ScreenResult } from "../lib/types";

type Filter = "setups" | "all";

export function Screener() {
  const { data } = useScreenStatus();
  const run = useRunScreen();
  const [filter, setFilter] = useState<Filter>("setups");

  const state = data?.state ?? "idle";
  const running = state === "running";
  const total = data?.total ?? 0;
  const done = data?.done ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  const results = data?.results ?? [];
  const complete = results.filter((r) => r.verdict === "COMPLETE SETUP").length;
  const watching = results.filter((r) => r.verdict === "WATCHING").length;

  const rows = useMemo(
    () =>
      filter === "setups"
        ? results.filter((r) => r.verdict !== "NO SETUP")
        : results,
    [results, filter],
  );

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight">
            <span className="text-gradient">S&P 500 Screener</span>
          </h1>
          <p className="mt-1.5 max-w-xl text-sm text-muted">
            Scans all ~500 S&P constituents through the Holy Grail engine and ranks every hit by
            weighted score. Data is weekly and cached hourly.
          </p>
        </div>
        <button
          onClick={() => run.mutate()}
          disabled={running || run.isPending}
          className="btn-primary whitespace-nowrap disabled:opacity-60"
        >
          {running ? `Scanning… ${pct}%` : results.length > 0 ? "Re-run scan" : "Run S&P 500 scan"}
        </button>
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
              <MiniStat label="Scanned" value={String(done)} />
              <MiniStat label="Complete" value={String(complete)} tint="#1fdd97" />
              <MiniStat label="Watching" value={String(watching)} tint="#ffb020" />
            </div>
            <div className="flex rounded-2xl border border-line bg-white/[0.02] p-1 text-sm">
              {(["setups", "all"] as Filter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-xl px-4 py-1.5 font-medium transition ${
                    filter === f ? "bg-white/[0.08] text-ink" : "text-muted hover:text-ink"
                  }`}
                >
                  {f === "setups" ? "Setups only" : "All"}
                </button>
              ))}
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
            Hit <span className="font-semibold text-ink">Run S&P 500 scan</span> to sweep the whole
            index for Holy Grail setups. First run takes a couple of minutes.
          </div>
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value, tint }: { label: string; value: string; tint?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white/[0.03] px-4 py-2.5 text-center">
      <div className="tnum font-display text-lg font-bold" style={tint ? { color: tint } : undefined}>
        {value}
      </div>
      <div className="text-[11px] text-faint">{label}</div>
    </div>
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
                      to={`/?ticker=${r.ticker}`}
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
