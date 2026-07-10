export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface LinePoint {
  time: string;
  value: number;
}

export interface CloudPoint {
  time: string;
  upper: number;
  lower: number;
  green: boolean;
}

export interface Marker {
  time: string;
  low: number;
  close: number;
}

export interface ScanSummary {
  weightedScore: number;
  totalWeight: number;
  verdict: "COMPLETE SETUP" | "WATCHING" | "NO SETUP";
  fullSetup: boolean;
  partialSetup: boolean;
  entryPriceLow: number;
  entryPriceHigh: number;
  stopPrice: number;
  lastClose: number;
  lastDate: string | null;
  lastHgDate: string | null;
  lastHgEntry: number | null;
  lastHgGainPct: number | null;
}

export interface DashboardRow {
  rule: string;
  status: string;
  value: string;
  passed: boolean;
}

export interface TableRow {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma50w: number | null;
  ema5: number | null;
  ema9: number | null;
  ema21: number | null;
  rsi14: number | null;
  pctAbove50w: number | null;
  mansfieldRs: number | null;
  weightedScore: number | null;
  fullSetup: boolean;
  partialSetup: boolean;
  hrr: boolean;
}

export interface ScanResponse {
  ticker: string;
  name: string;
  history: string;
  summary: ScanSummary;
  candles: Candle[];
  cloud: CloudPoint[];
  ma50w: LinePoint[];
  ema5: LinePoint[];
  ema9: LinePoint[];
  ema21: LinePoint[];
  markers: {
    fullSetup: Marker[];
    partial: Marker[];
    hrr: Marker[];
  };
  dashboard: DashboardRow[];
  table: TableRow[];
  settings: { retestMax: number; fullThresh: number; partialThresh: number };
  insufficientData?: boolean;
}

export interface AiPanel {
  html: string;
  source: string;
}

export interface AiResponse {
  technical: AiPanel;
  fundamental: AiPanel;
  narrative: AiPanel;
}

export interface WatchlistItem {
  ticker: string;
  dateAdded: string;
  priceAdded: number;
  priceTarget: number | null;
  options?: string;
  currentPrice: number | null;
  verdict: "BUY" | "WATCH" | "HOLD" | "TRIM" | "SELL" | "AVOID" | string;
  commentary: string;
  gain: number | null;
}

export interface WatchlistResponse {
  items: WatchlistItem[];
  githubEnabled: boolean;
}

export type HistoryRange = "3M" | "6M" | "YTD" | "1Y" | "2Y" | "5Y";

export interface ScreenResult {
  ticker: string;
  score: number;
  verdict: "COMPLETE SETUP" | "WATCHING" | "NO SETUP";
  fullSetup: boolean;
  partialSetup: boolean;
  weeksSinceLastFull: number | null;
  lastClose: number | null;
  entryLow: number | null;
  entryHigh: number | null;
  mansfieldRs: number | null;
  pctAbove50w: number | null;
  rsi14: number | null;
}

export interface ScreenStatus {
  state: "idle" | "running" | "done" | "error";
  universe?: string;
  total: number;
  done: number;
  found: number;
  results: ScreenResult[];
  elapsed: number | null;
  error: string | null;
}
