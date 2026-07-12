import { useState } from "react";
import { Link } from "react-router-dom";
import {
  lookupPrice,
  useAddWatchlist,
  useRemoveWatchlist,
  useSellWatchlist,
  useWatchlist,
  verifyAdminPassword,
} from "../lib/api";
import { fmtPct, fmtUsd, gainColor, WL_VERDICT_COLOR } from "../lib/format";
import type { WatchlistItem } from "../lib/types";

const VERDICTS = ["BUY", "WATCH", "HOLD", "TRIM", "SELL", "AVOID"];

export function ExpertCorner() {
  const { data, isLoading } = useWatchlist();
  const items = data?.items ?? [];
  const [tab, setTab] = useState<"active" | "closed">("active");

  const activeItems = items.filter((i) => i.status !== "closed");
  const allSells = items.flatMap((item) => 
    (item.sells || []).map((sell) => ({
      ticker: item.ticker,
      originalEntry: item.priceAdded,
      sellDate: sell.date,
      sellPercent: sell.percent,
      sellPrice: sell.price,
      realizedReturn: item.priceAdded ? ((sell.price - item.priceAdded) / item.priceAdded) * 100 : null
    }))
  ).sort((a, b) => b.sellDate.localeCompare(a.sellDate));

  const winners = activeItems.filter((i) => (i.gain ?? 0) > 0).length;
  const avgGain =
    activeItems.length > 0
      ? activeItems.reduce((a, i) => a + (i.gain ?? 0), 0) / activeItems.filter((i) => i.gain !== null).length
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
              tooltip="assuming $100 to every ticker"
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
        <div className="space-y-4">
          <div className="flex border-b border-line-strong text-sm font-semibold">
            <button
              onClick={() => setTab("active")}
              className={`px-4 py-2 hover:text-bull transition ${tab === "active" ? "border-b-2 border-bull text-bull" : "text-muted"}`}
            >
              Active Setups ({activeItems.length})
            </button>
            <button
              onClick={() => setTab("closed")}
              className={`px-4 py-2 hover:text-info transition ${tab === "closed" ? "border-b-2 border-info text-info" : "text-muted"}`}
            >
              Closed Trades ({allSells.length})
            </button>
          </div>
          
          {tab === "active" ? (
            activeItems.length > 0 ? <WatchTable items={activeItems} /> : <div className="text-sm text-muted">No active setups.</div>
          ) : (
            allSells.length > 0 ? <ClosedTable sells={allSells} /> : <div className="text-sm text-muted">No closed trades.</div>
          )}
        </div>
      )}

      <AdminPanel items={activeItems} githubEnabled={data?.githubEnabled ?? false} />
    </div>
  );
}

function MiniStat({
  label,
  value,
  tint,
  tooltip,
}: {
  label: string;
  value: string;
  tint?: string;
  tooltip?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative rounded-2xl border border-line bg-white/[0.03] px-4 py-2.5 text-center">
      <div className="tnum font-display text-lg font-bold" style={tint ? { color: tint } : undefined}>
        {value}
      </div>
      <div className="flex items-center justify-center gap-1 text-[11px] text-faint select-none">
        <span>{label}</span>
        {tooltip && (
          <button
            onClick={() => setShow((s) => !s)}
            onBlur={() => setTimeout(() => setShow(false), 200)}
            className="text-[10px] opacity-60 hover:opacity-100 transition focus:outline-none"
            title={tooltip}
          >
            ℹ️
          </button>
        )}
      </div>
      {show && tooltip && (
        <div className="absolute left-1/2 bottom-full mb-2 w-48 -translate-x-1/2 rounded-lg border border-line-strong bg-[#0f172a] p-2 text-center text-[10px] text-muted shadow-2xl z-20 animate-fade-in">
          {tooltip}
        </div>
      )}
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
              <th className="px-4 py-3 font-semibold">Verdict <span className="text-[9px] text-faint normal-case font-normal block mt-0.5">(hover for comments)</span></th>
              <th className="px-4 py-3 font-semibold">Gain / Loss</th>
              <th className="px-4 py-3 font-semibold">Resistance <span className="text-[9px] text-faint normal-case font-normal block mt-0.5">(price rejection pt)</span></th>
              <th className="px-4 py-3 font-semibold">Options</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => {
              const color = WL_VERDICT_COLOR[r.verdict] ?? "#888";
              return (
                <tr key={r.ticker} className="border-b border-line/50 transition hover:bg-white/[0.02]">
                  <td className="px-4 py-3 text-muted">{r.dateAdded}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/scanner?ticker=${r.ticker}`}
                        className="rounded-md border border-info/20 bg-info/10 px-2 py-1 font-bold text-info transition hover:bg-info/20"
                      >
                        {r.ticker}
                      </Link>
                      {r.positionSize < 100 && (
                        <span className="rounded bg-white/10 px-1.5 py-0.5 text-[9px] font-bold text-muted">
                          {r.positionSize}% left
                        </span>
                      )}
                    </div>
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
                  <td className="px-4 py-3 text-muted font-bold">
                    {r.priceTarget === null || r.priceTarget === undefined ? "-" : fmtUsd(r.priceTarget)}
                  </td>
                  <td className="px-4 py-3 text-muted font-bold">
                    {r.options || "-"}
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

function ClosedTable({
  sells,
}: {
  sells: {
    ticker: string;
    originalEntry: number;
    sellDate: string;
    sellPercent: number;
    sellPrice: number;
    realizedReturn: number | null;
  }[];
}) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line-strong text-left text-[11px] uppercase tracking-wider text-faint">
              <th className="px-4 py-3 font-semibold">Date Closed</th>
              <th className="px-4 py-3 font-semibold">Ticker</th>
              <th className="px-4 py-3 font-semibold">Portion Sold</th>
              <th className="px-4 py-3 font-semibold">Sell Price</th>
              <th className="px-4 py-3 font-semibold">Original Entry</th>
              <th className="px-4 py-3 font-semibold">Realized Return</th>
            </tr>
          </thead>
          <tbody>
            {sells.map((s, i) => (
              <tr key={`${s.ticker}-${i}`} className="border-b border-line/50 transition hover:bg-white/[0.02]">
                <td className="px-4 py-3 text-muted">{s.sellDate}</td>
                <td className="px-4 py-3">
                  <Link
                    to={`/scanner?ticker=${s.ticker}`}
                    className="rounded-md border border-info/20 bg-info/10 px-2 py-1 font-bold text-info transition hover:bg-info/20"
                  >
                    {s.ticker}
                  </Link>
                </td>
                <td className="px-4 py-3 text-muted">{s.sellPercent}%</td>
                <td className="px-4 py-3 text-muted">{fmtUsd(s.sellPrice)}</td>
                <td className="px-4 py-3 text-muted">{fmtUsd(s.originalEntry)}</td>
                <td className={`px-4 py-3 font-bold ${gainColor(s.realizedReturn)}`}>
                  {s.realizedReturn === null ? "N/A" : fmtPct(s.realizedReturn)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AdminPanel({ items, githubEnabled }: { items: WatchlistItem[]; githubEnabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [pass, setPass] = useState("");
  const [isVerified, setIsVerified] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [ticker, setTicker] = useState("NVDA");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [verdict, setVerdict] = useState("WATCH");
  const [commentary, setCommentary] = useState("");
  const [price, setPrice] = useState("0");
  const [targetPrice, setTargetPrice] = useState("");
  const [optionsContract, setOptionsContract] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [sellTicker, setSellTicker] = useState(items[0]?.ticker ?? "");
  const [sellPercent, setSellPercent] = useState("100");

  const add = useAddWatchlist();
  const remove = useRemoveWatchlist();
  const sell = useSellWatchlist();

  const flash = (ok: boolean, text: string) => {
    setMsg({ ok, text });
    setTimeout(() => setMsg(null), 4000);
  };

  const handleVerify = async () => {
    if (!pass) return;
    setVerifying(true);
    const ok = await verifyAdminPassword(pass);
    setVerifying(false);
    if (ok) {
      setIsVerified(true);
      flash(true, "Password verified successfully.");
    } else {
      setIsVerified(false);
      flash(false, "Incorrect admin password.");
    }
  };

  const handlePassChange = (val: string) => {
    setPass(val);
    setIsVerified(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleVerify();
    }
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
          price_target: targetPrice.trim() !== "" ? Number(targetPrice) : null,
          options: optionsContract.trim() !== "" ? optionsContract : null,
          verdict,
          commentary,
        },
        admin: pass,
      });
      flash(true, `Saved ${ticker.toUpperCase()}`);
      setCommentary("");
      setTargetPrice("");
      setOptionsContract("");
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

  const handleSell = async () => {
    if (!sellTicker || !sellPercent) return;
    try {
      await sell.mutateAsync({ ticker: sellTicker, percent: parseFloat(sellPercent), admin: pass });
      flash(true, `Sold ${sellPercent}% of ${sellTicker}`);
      setSellPercent("100");
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
          {!isVerified ? (
            <div className="space-y-3">
              <div className="text-xs text-muted font-semibold block mb-1">Verify Password to Unlock</div>
              <div className="flex gap-2 max-w-sm">
                <input
                  type="password"
                  value={pass}
                  onChange={(e) => handlePassChange(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Admin password"
                  className="input flex-1"
                />
                <button
                  onClick={handleVerify}
                  disabled={verifying || !pass}
                  className="btn-primary shrink-0 text-xs px-4"
                >
                  {verifying ? "Verifying..." : "Unlock"}
                </button>
              </div>
              {msg && (
                <div className={`text-sm ${msg.ok ? "text-bull" : "text-bear"}`}>{msg.text}</div>
              )}
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between text-xs bg-white/[0.02] border border-line rounded-lg px-3 py-2">
                <span className="text-bull font-semibold">🔐 Admin Access Unlocked</span>
                <button
                  onClick={() => {
                    setIsVerified(false);
                    setPass("");
                  }}
                  className="text-bear hover:underline font-semibold"
                >
                  Lock
                </button>
              </div>

              {msg && (
                <div className={`text-sm ${msg.ok ? "text-bull" : "text-bear"}`}>{msg.text}</div>
              )}

              <div className="grid gap-6 md:grid-cols-3">
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
                    <label className="text-xs text-muted">
                      <span className="mb-1 block">Resistance <span className="text-[10px] text-muted normal-case font-normal">(price rejection pt)</span></span>
                      <input
                        type="number"
                        step="0.01"
                        value={targetPrice}
                        onChange={(e) => setTargetPrice(e.target.value)}
                        placeholder="None (-)"
                        className="input"
                      />
                    </label>
                    <label className="text-xs text-muted">
                      <span className="mb-1 block">Options contract</span>
                      <input
                        value={optionsContract}
                        onChange={(e) => setOptionsContract(e.target.value)}
                        placeholder="None (-)"
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

                {/* Sell */}
                <div className="space-y-3">
                  <div className="text-sm font-semibold text-muted">💰 Sell / Take Profit</div>
                  {items.length === 0 ? (
                    <div className="text-sm text-muted">No active setups to sell.</div>
                  ) : (
                    <div className="space-y-3">
                      <label className="text-xs text-muted block">
                        <span className="mb-1 block">Select Ticker</span>
                        <select
                          value={sellTicker}
                          onChange={(e) => setSellTicker(e.target.value)}
                          className="input"
                        >
                          {sellTicker === "" && <option value="" disabled>Select...</option>}
                          {items.map((i) => (
                            <option key={i.ticker} value={i.ticker}>
                              {i.ticker} ({i.positionSize}% left)
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="text-xs text-muted block">
                        <span className="mb-1 block">Percent to Sell (0-100%)</span>
                        <input
                          type="number"
                          step="1"
                          min="1"
                          max="100"
                          value={sellPercent}
                          onChange={(e) => setSellPercent(e.target.value)}
                          className="input"
                        />
                      </label>
                      <button
                        onClick={handleSell}
                        disabled={sell.isPending || !pass || !sellTicker}
                        className="btn-bull text-xs"
                      >
                        {sell.isPending ? "Selling…" : "Sell Position"}
                      </button>
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
            </>
          )}
        </div>
      )}
    </div>
  );
}
