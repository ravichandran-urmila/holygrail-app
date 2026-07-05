import { useState } from "react";
import { Link } from "react-router-dom";
import {
  lookupPrice,
  useAddWatchlist,
  useRemoveWatchlist,
  useWatchlist,
} from "../lib/api";
import { fmtPct, fmtUsd, gainColor, WL_VERDICT_COLOR } from "../lib/format";
import type { WatchlistItem } from "../lib/types";

const VERDICTS = ["BUY", "WATCH", "HOLD", "AVOID"];

export function ExpertCorner() {
  const { data, isLoading } = useWatchlist();
  const items = data?.items ?? [];

  const winners = items.filter((i) => (i.gain ?? 0) > 0).length;
  const avgGain =
    items.length > 0
      ? items.reduce((a, i) => a + (i.gain ?? 0), 0) / items.filter((i) => i.gain !== null).length
      : 0;

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight">
            <span className="text-gradient">Expert Corner</span>
          </h1>
          <p className="mt-1.5 max-w-xl text-sm text-muted">
            A curated list of high-conviction tickers with entry prices and live returns.
          </p>
        </div>
        {items.length > 0 && (
          <div className="flex gap-3">
            <MiniStat label="Tracked" value={String(items.length)} />
            <MiniStat label="In profit" value={`${winners}/${items.length}`} tint="#1fdd97" />
            <MiniStat
              label="Avg return"
              value={fmtPct(avgGain)}
              tint={avgGain >= 0 ? "#1fdd97" : "#ff5470"}
            />
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="skeleton h-64" />
      ) : items.length === 0 ? (
        <div className="card p-6 text-sm text-muted">
          Expert Corner is currently empty. Add tickers in the admin panel below.
        </div>
      ) : (
        <WatchTable items={items} />
      )}

      <AdminPanel items={items} githubEnabled={data?.githubEnabled ?? false} />
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

function WatchTable({ items }: { items: WatchlistItem[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line-strong text-left text-[11px] uppercase tracking-wider text-faint">
              <th className="px-4 py-3 font-semibold">Date</th>
              <th className="px-4 py-3 font-semibold">Ticker</th>
              <th className="px-4 py-3 font-semibold">Price Added</th>
              <th className="px-4 py-3 font-semibold">Current</th>
              <th className="px-4 py-3 font-semibold">Verdict</th>
              <th className="px-4 py-3 font-semibold">Gain / Loss</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => {
              const color = WL_VERDICT_COLOR[r.verdict] ?? "#888";
              return (
                <tr key={r.ticker} className="border-b border-line/50 transition hover:bg-white/[0.02]">
                  <td className="px-4 py-3 text-muted">{r.dateAdded}</td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/?ticker=${r.ticker}`}
                      className="rounded-md border border-info/20 bg-info/10 px-2 py-1 font-bold text-info transition hover:bg-info/20"
                    >
                      {r.ticker}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{fmtUsd(r.priceAdded)}</td>
                  <td className="px-4 py-3">{r.currentPrice === null ? "N/A" : fmtUsd(r.currentPrice)}</td>
                  <td className="px-4 py-3">
                    <span
                      title={r.commentary || undefined}
                      className={`rounded-md border px-2.5 py-1 text-xs font-bold ${
                        r.commentary ? "cursor-help underline decoration-dotted underline-offset-2" : ""
                      }`}
                      style={{ color, borderColor: `${color}40`, background: "rgba(255,255,255,0.03)" }}
                    >
                      {r.verdict}
                    </span>
                  </td>
                  <td className={`px-4 py-3 font-bold ${gainColor(r.gain)}`}>
                    {r.gain === null ? "N/A" : fmtPct(r.gain)}
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

function AdminPanel({ items, githubEnabled }: { items: WatchlistItem[]; githubEnabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [pass, setPass] = useState("");
  const [ticker, setTicker] = useState("NVDA");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [verdict, setVerdict] = useState("WATCH");
  const [commentary, setCommentary] = useState("");
  const [price, setPrice] = useState("0");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const add = useAddWatchlist();
  const remove = useRemoveWatchlist();

  const flash = (ok: boolean, text: string) => {
    setMsg({ ok, text });
    setTimeout(() => setMsg(null), 4000);
  };

  const autoFetch = async () => {
    try {
      const p = await lookupPrice(ticker.trim().toUpperCase(), date, pass);
      setPrice(p.toFixed(2));
      flash(true, `Fetched $${p.toFixed(2)}`);
    } catch (e) {
      flash(false, (e as Error).message);
    }
  };

  const save = async () => {
    try {
      await add.mutateAsync({
        item: {
          ticker: ticker.trim().toUpperCase(),
          date_added: date,
          price_added: Number(price),
          verdict,
          commentary,
        },
        admin: pass,
      });
      flash(true, `Saved ${ticker.toUpperCase()}`);
      setCommentary("");
    } catch (e) {
      flash(false, (e as Error).message);
    }
  };

  const del = async (t: string) => {
    try {
      await remove.mutateAsync({ ticker: t, admin: pass });
      flash(true, `Removed ${t}`);
    } catch (e) {
      flash(false, (e as Error).message);
    }
  };

  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-5 py-4 text-left text-sm font-semibold"
      >
        <span>🛠️ Admin Controls</span>
        <span className="text-muted">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="space-y-5 border-t border-line p-5">
          <input
            type="password"
            value={pass}
            onChange={(e) => setPass(e.target.value)}
            placeholder="Admin password"
            className="input max-w-xs"
          />

          {msg && (
            <div className={`text-sm ${msg.ok ? "text-bull" : "text-bear"}`}>{msg.text}</div>
          )}

          <div className="grid gap-6 md:grid-cols-2">
            {/* Add */}
            <div className="space-y-3">
              <div className="text-sm font-semibold text-muted">➕ Add / update ticker</div>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-xs text-muted">
                  <span className="mb-1 block">Ticker</span>
                  <input
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    className="input"
                  />
                </label>
                <label className="text-xs text-muted">
                  <span className="mb-1 block">Date added</span>
                  <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="input" />
                </label>
                <label className="text-xs text-muted">
                  <span className="mb-1 block">Verdict</span>
                  <select value={verdict} onChange={(e) => setVerdict(e.target.value)} className="input">
                    {VERDICTS.map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-xs text-muted">
                  <span className="mb-1 block">Price added</span>
                  <input
                    type="number"
                    step="0.01"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    className="input"
                  />
                </label>
              </div>
              <label className="block text-xs text-muted">
                <span className="mb-1 block">Commentary (tooltip)</span>
                <textarea
                  value={commentary}
                  onChange={(e) => setCommentary(e.target.value)}
                  rows={3}
                  className="input resize-none"
                  placeholder="Thesis shown on hover…"
                />
              </label>
              <div className="flex gap-2">
                <button onClick={autoFetch} className="btn-ghost text-xs" disabled={!pass}>
                  🔍 Auto-fetch price
                </button>
                <button onClick={save} className="btn-primary text-xs" disabled={add.isPending || !pass}>
                  {add.isPending ? "Saving…" : "Save"}
                </button>
              </div>
            </div>

            {/* Remove */}
            <div className="space-y-3">
              <div className="text-sm font-semibold text-muted">❌ Remove ticker</div>
              {items.length === 0 ? (
                <div className="text-sm text-muted">Nothing to remove.</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {items.map((i) => (
                    <button
                      key={i.ticker}
                      onClick={() => del(i.ticker)}
                      disabled={remove.isPending || !pass}
                      className="chip transition hover:border-bear/50 hover:text-bear disabled:opacity-40"
                    >
                      {i.ticker} ✕
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div
            className={`rounded-lg border px-3 py-2 text-xs ${
              githubEnabled ? "border-bull/30 bg-bull/5 text-bull" : "border-gold/30 bg-gold/5 text-gold"
            }`}
          >
            {githubEnabled
              ? "✅ GitHub persistence active — changes survive redeploys."
              : "⚠️ GitHub persistence not configured — changes save to the local file only."}
          </div>
        </div>
      )}
    </div>
  );
}
