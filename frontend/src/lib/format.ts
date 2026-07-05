export const fmtUsd = (v: number | null | undefined, digits = 2): string =>
  v === null || v === undefined || Number.isNaN(v)
    ? "N/A"
    : `$${v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;

export const fmtPct = (v: number | null | undefined, digits = 2): string =>
  v === null || v === undefined || Number.isNaN(v)
    ? "N/A"
    : `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;

export const gainColor = (v: number | null | undefined): string =>
  v === null || v === undefined ? "text-faint" : v >= 0 ? "text-bull" : "text-bear";

export const VERDICT_META: Record<
  string,
  { label: string; color: string; hex: string; emoji: string }
> = {
  "COMPLETE SETUP": { label: "Complete Setup", color: "text-bull", hex: "#1fdd97", emoji: "🚀" },
  WATCHING: { label: "Watching", color: "text-gold", hex: "#ffb020", emoji: "👀" },
  "NO SETUP": { label: "No Setup", color: "text-[#94a6c9]", hex: "#94a6c9", emoji: "◦" },
};

export const WL_VERDICT_COLOR: Record<string, string> = {
  BUY: "#16c784",
  WATCH: "#ffd23f",
  HOLD: "#38b6ff",
  AVOID: "#ea3943",
};
