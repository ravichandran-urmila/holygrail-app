import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { useScan } from "../lib/api";
import { useSettings } from "../lib/settings";
import { Chart } from "../components/Chart";
import { AiPanels } from "../components/AiPanels";
import { fmtPct, fmtUsd, gainColor, VERDICT_META } from "../lib/format";
import type { HistoryRange, ScanResponse } from "../lib/types";

const RANGES: HistoryRange[] = ["3M", "6M", "YTD", "1Y", "2Y", "5Y"];
const TABS = ["Chart", "Dashboard", "Data"] as const;

export function Scanner() {
  const [params, setParams] = useSearchParams();
  const urlTicker = (params.get("ticker") ?? "NVDA").toUpperCase();
  const [input, setInput] = useState(urlTicker);
  const [range, setRange] = useState<HistoryRange>("1Y");
  const urlTab = params.get("tab");
  const initialTab = urlTab === "Dashboard" || urlTab === "Data" ? urlTab : "Chart";
  const [tab, setTab] = useState<(typeof TABS)[number]>(initialTab);
  const { settings, showCloud } = useSettings();

  useEffect(() => setInput(urlTicker), [urlTicker]);

  const { data, isLoading, isError, error } = useScan(urlTicker, range, settings, true);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = input.trim().toUpperCase();
    if (t) setParams({ ticker: t });
  };

  return (
    <div className="space-y-6">
      <form onSubmit={submit} className="animate-fade-up flex flex-wrap items-center gap-3">
        <div className="relative min-w-[240px] flex-1">
          <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-lg text-faint">
            🔎
          </span>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            placeholder="Search any ticker — AAPL, NVDA, ARM…"
            className="input h-14 rounded-3xl pl-12 text-lg font-semibold tracking-wide"
            spellCheck={false}
          />
        </div>
        <button type="submit" className="btn-primary h-14 rounded-3xl px-8">
          Scan
        </button>
      </form>

      {isError && (
        <div className="card border-bear/30 p-6 text-sm text-bear">
          Could not load <strong>{urlTicker}</strong> — {(error as Error)?.message}
        </div>
      )}

      {isLoading && <ScanSkeleton />}

      {data && !isError && (
        <div className="space-y-6">
          <Hero data={data} />
          <MetricRow data={data} />

          <div className="card animate-fade-up overflow-hidden">
            <div className="flex flex-wrap items-center gap-3 border-b border-line px-4 py-3 sm:px-5">
              <div className="flex rounded-2xl border border-line bg-white/[0.02] p-1">
                {TABS.map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`rounded-xl px-4 py-1.5 text-sm font-semibold transition ${
                      tab === t ? "bg-white/[0.09] text-ink" : "text-muted hover:text-ink"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>

              {tab === "Chart" && (
                <div className="ml-auto flex items-center gap-2">
                  <div className="flex rounded-2xl border border-line bg-white/[0.02] p-1">
                    {RANGES.map((r) => (
                      <button
                        key={r}
                        onClick={() => setRange(r)}
                        className={`rounded-xl px-2.5 py-1.5 text-xs font-bold transition ${
                          range === r ? "bg-violet/25 text-ink" : "text-muted hover:text-ink"
                        }`}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="p-3 sm:p-5">
              {tab === "Chart" && (
                <>
                  <Chart data={data} showCloud={showCloud} />
                  <ChartLegend />
                </>
              )}
              {tab === "Dashboard" && <DashboardTab data={data} />}
              {tab === "Data" && <DataTab data={data} />}
            </div>
          </div>

          {tab === "Chart" && (
            <div className="animate-fade-up">
              <h2 className="mb-3 flex items-center gap-2 text-lg font-bold">
                <span className="text-gradient">AI Insights</span>
                <span className="chip">3 analysts</span>
              </h2>
              <AiPanels ticker={urlTicker} enabled={!!data} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function useWeekChange(data: ScanResponse): number | null {
  return useMemo(() => {
    const c = data.candles;
    if (c.length < 2) return null;
    const prev = c[c.length - 2].close;
    const last = c[c.length - 1].close;
    if (!prev) return null;
    return ((last - prev) / prev) * 100;
  }, [data]);
}

function Hero({ data }: { data: ScanResponse }) {
  const s = data.summary;
  const meta = VERDICT_META[s.verdict] ?? VERDICT_META["NO SETUP"];
  const week = useWeekChange(data);
  const pct = s.weightedScore && s.totalWeight ? (s.weightedScore / s.totalWeight) * 100 : 0;

  return (
    <div className="animate-fade-up relative overflow-hidden rounded-4xl border border-line bg-surface/70 p-6 shadow-card backdrop-blur-xl sm:p-8">
      <div
        className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full opacity-40 blur-3xl"
        style={{
          background:
            s.verdict === "COMPLETE SETUP"
              ? "radial-gradient(circle, #1fdd97, transparent 70%)"
              : s.verdict === "WATCHING"
                ? "radial-gradient(circle, #ffb020, transparent 70%)"
                : "radial-gradient(circle, #7c5cff, transparent 70%)",
        }}
      />
      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <span className="font-display text-2xl font-bold tracking-tight">{data.ticker}</span>
            <span className="truncate text-sm text-muted">{data.name}</span>
          </div>
          <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="tnum font-display text-5xl font-bold tracking-tight sm:text-6xl">
              {fmtUsd(s.lastClose)}
            </span>
            {week !== null && (
              <span className={`tnum text-lg font-semibold ${gainColor(week)}`}>
                {week >= 0 ? "▲" : "▼"} {fmtPct(week)}
                <span className="ml-1 text-sm font-normal text-faint">this week</span>
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-col items-start gap-4 lg:items-end">
          <span
            className={`inline-flex items-center gap-2 rounded-2xl border px-5 py-2.5 text-base font-bold ${meta.color}`}
            style={{
              borderColor: `${meta.hex}66`,
              background: `${meta.hex}1a`,
              boxShadow: `0 10px 34px -12px ${meta.hex}`,
            }}
          >
            <span className="text-xl">{meta.emoji}</span>
            {meta.label}
          </span>
          <ScoreMeter score={s.weightedScore ?? 0} total={s.totalWeight ?? 1} pct={pct} data={data} />
        </div>
      </div>
    </div>
  );
}

function ScoreMeter({
  score,
  total,
  pct,
  data,
}: {
  score: number;
  total: number;
  pct: number;
  data: ScanResponse;
}) {
  const partial = (data.settings.partialThresh / total) * 100;
  const full = (data.settings.fullThresh / total) * 100;
  return (
    <div className="w-full min-w-[240px] lg:w-72">
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="text-faint">Weighted score</span>
        <span className="tnum font-semibold text-ink">
          {score.toFixed(2)} <span className="text-faint">/ {total.toFixed(2)}</span>
        </span>
      </div>
      <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${Math.min(100, pct)}%`,
            background: "linear-gradient(90deg, #7c5cff, #22d3ee, #1fdd97)",
          }}
        />
        <span className="absolute top-0 h-full w-px bg-white/40" style={{ left: `${partial}%` }} />
        <span className="absolute top-0 h-full w-px bg-white/60" style={{ left: `${full}%` }} />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-faint">
        <span>watch {data.settings.partialThresh}</span>
        <span>full {data.settings.fullThresh}</span>
      </div>
    </div>
  );
}

function MetricRow({ data }: { data: ScanResponse }) {
  const s = data.summary;
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <MetricCard
        icon="🎯"
        tint="#1fdd97"
        label="Gain from HG signal"
        value={
          s.lastHgGainPct === null ? (
            <span className="text-faint">N/A</span>
          ) : (
            <span className={gainColor(s.lastHgGainPct)}>{fmtPct(s.lastHgGainPct)}</span>
          )
        }
        sub={s.lastHgDate ? `${fmtUsd(s.lastHgEntry)} · ${s.lastHgDate}` : "No signals in history"}
      />
      <MetricCard
        icon="📈"
        tint="#7c5cff"
        label="Entry range (50WMA zone)"
        value={`${fmtUsd(s.entryPriceLow)} – ${fmtUsd(s.entryPriceHigh)}`}
        sub={`up to +${data.settings.retestMax}% above the 50-week MA`}
      />
      <MetricCard
        icon="🛑"
        tint="#ff5470"
        label="Stop loss (weekly close)"
        value={<span className="text-bear">{fmtUsd(s.stopPrice)}</span>}
        sub="0.5% below the 50-week MA"
      />
    </div>
  );
}

function MetricCard({
  icon,
  tint,
  label,
  value,
  sub,
}: {
  icon: string;
  tint: string;
  label: string;
  value: React.ReactNode;
  sub?: string;
}) {
  return (
    <div className="card card-hover animate-fade-up p-5">
      <div className="mb-3 flex items-center gap-2.5">
        <span
          className="grid h-9 w-9 place-items-center rounded-xl text-base"
          style={{ background: `${tint}1f`, boxShadow: `inset 0 0 0 1px ${tint}33` }}
        >
          {icon}
        </span>
        <span className="text-xs font-medium text-muted">{label}</span>
      </div>
      <div className="tnum font-display text-2xl font-bold tracking-tight">{value}</div>
      {sub && <div className="mt-1 text-xs text-faint">{sub}</div>}
    </div>
  );
}

function ChartLegend() {
  const items = [
    { s: <span className="text-[#5b6bff]">▲</span>, t: "HG — Full Setup (best entry)" },
    { s: <span className="text-gold">●</span>, t: "Partial Setup (watching)" },
    { s: <span style={{ color: "#e879f9" }}>■</span>, t: "HRR — high risk / reward" },
    { s: <span className="text-[#ff9f0a]">━</span>, t: "50-week MA" },
  ];
  return (
    <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 px-1 text-xs text-muted">
      {items.map((i) => (
        <span key={i.t} className="inline-flex items-center gap-1.5">
          {i.s} {i.t}
        </span>
      ))}
    </div>
  );
}

function DashboardTab({ data }: { data: ScanResponse }) {
  const s = data.summary;
  return (
    <div>
      <div className="mb-4 text-sm font-semibold text-muted">Rule dashboard · latest weekly bar</div>
      <div className="grid gap-3 sm:grid-cols-2">
        {data.dashboard.map((r) => (
          <div
            key={r.rule}
            className={`rounded-2xl border p-4 ${
              r.passed ? "border-bull/25 bg-bull/[0.06]" : "border-white/5 bg-white/[0.015]"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">{r.rule}</span>
              <span
                className={`rounded-lg px-2 py-0.5 text-xs font-bold ${
                  r.passed ? "bg-bull/20 text-bull" : "bg-bear/15 text-bear"
                }`}
              >
                {r.passed ? "PASS" : "FAIL"}
              </span>
            </div>
            <div className="mt-1.5 text-xs text-muted">{r.value}</div>
          </div>
        ))}
      </div>
      <div className="mt-5 rounded-2xl border border-line bg-white/[0.02] p-4">
        <div className="text-sm">
          <span className="font-semibold">Weighted score:</span>{" "}
          <span className="tnum">
            {s.weightedScore?.toFixed(2)} / {s.totalWeight?.toFixed(2)}
          </span>{" "}
          → <span className={VERDICT_META[s.verdict]?.color}>{VERDICT_META[s.verdict]?.label}</span>
        </div>
        <div className="mt-1 text-xs text-muted">
          Suggested entry {fmtUsd(s.entryPriceLow)} – {fmtUsd(s.entryPriceHigh)} · stop{" "}
          {fmtUsd(s.stopPrice)} on a weekly close.
        </div>
      </div>
    </div>
  );
}

function DataTab({ data }: { data: ScanResponse }) {
  const cols: { key: keyof ScanResponse["table"][number]; label: string; fmt?: (v: number) => string }[] = [
    { key: "date", label: "Date" },
    { key: "close", label: "Close", fmt: (v) => v.toFixed(2) },
    { key: "ma50w", label: "50WMA", fmt: (v) => v.toFixed(2) },
    { key: "ema5", label: "EMA5", fmt: (v) => v.toFixed(2) },
    { key: "ema21", label: "EMA21", fmt: (v) => v.toFixed(2) },
    { key: "rsi14", label: "RSI", fmt: (v) => v.toFixed(1) },
    { key: "pctAbove50w", label: "% 50WMA", fmt: (v) => v.toFixed(1) },
    { key: "mansfieldRs", label: "Mansfield", fmt: (v) => v.toFixed(2) },
    { key: "weightedScore", label: "Score", fmt: (v) => v.toFixed(2) },
  ];

  const downloadCsv = () => {
    const header = Object.keys(data.table[0] ?? {}).join(",");
    const body = data.table.map((r) => Object.values(r).join(",")).join("\n");
    const blob = new Blob([`${header}\n${body}`], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.ticker}_holygrail.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm font-semibold text-muted">Weekly series · latest first</span>
        <button onClick={downloadCsv} className="btn-ghost !rounded-xl !px-3 !py-2 text-xs">
          ⬇ Download CSV
        </button>
      </div>
      <div className="max-h-[520px] overflow-auto rounded-2xl border border-line">
        <table className="w-full border-collapse text-right text-xs">
          <thead className="sticky top-0 bg-surface-2 text-faint">
            <tr>
              {cols.map((c) => (
                <th key={String(c.key)} className="px-3 py-2.5 font-semibold first:text-left">
                  {c.label}
                </th>
              ))}
              <th className="px-3 py-2.5 text-center font-semibold">Signal</th>
            </tr>
          </thead>
          <tbody className="tnum font-mono">
            {data.table.map((row) => (
              <tr key={row.date} className="border-t border-line/50 hover:bg-white/[0.02]">
                {cols.map((c) => {
                  const v = row[c.key];
                  return (
                    <td key={String(c.key)} className="px-3 py-1.5 first:text-left">
                      {v === null || v === undefined
                        ? "—"
                        : typeof v === "number" && c.fmt
                          ? c.fmt(v)
                          : String(v)}
                    </td>
                  );
                })}
                <td className="px-3 py-1.5 text-center">
                  {row.fullSetup && <span className="text-[#5b6bff]">▲</span>}
                  {row.partialSetup && <span className="text-gold">●</span>}
                  {row.hrr && <span style={{ color: "#e879f9" }}>■</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ScanSkeleton() {
  return (
    <div className="space-y-6">
      <div className="skeleton h-40 rounded-4xl" />
      <div className="grid gap-4 sm:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="skeleton h-28" />
        ))}
      </div>
      <div className="skeleton h-[560px]" />
    </div>
  );
}
