import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  AiResponse,
  HistoryRange,
  ScanResponse,
  ScreenStatus,
  WatchlistItem,
  WatchlistResponse,
} from "./types";
import { settingsToQuery, type Settings } from "./settings";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

async function send<T>(path: string, method: string, body: unknown, admin?: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(admin ? { "X-Admin-Password": admin } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function useScan(
  ticker: string,
  history: HistoryRange,
  settings: Settings,
  enabled: boolean,
) {
  const q = settingsToQuery(settings);
  return useQuery({
    queryKey: ["scan", ticker, history, q],
    queryFn: () =>
      get<ScanResponse>(
        `/api/scan?ticker=${encodeURIComponent(ticker)}&history=${history}&${q}`,
      ),
    enabled: enabled && ticker.length > 0,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useAi(ticker: string, enabled: boolean) {
  return useQuery({
    queryKey: ["ai", ticker],
    queryFn: () => get<AiResponse>(`/api/scan/${encodeURIComponent(ticker)}/ai`),
    enabled: enabled && ticker.length > 0,
    staleTime: 10 * 60 * 1000,
    retry: 0,
  });
}

export function useGuideCase(ticker: string, start: string, end: string) {
  return useQuery({
    queryKey: ["guide", ticker, start, end],
    queryFn: () =>
      get<ScanResponse>(`/api/guide/${ticker}?start=${start}&end=${end}`),
    staleTime: 60 * 60 * 1000,
    retry: 1,
  });
}

export function useWatchlist() {
  return useQuery({
    queryKey: ["watchlist"],
    queryFn: () => get<WatchlistResponse>("/api/watchlist"),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useAddWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { item: Record<string, unknown>; admin: string }) =>
      send<WatchlistResponse>("/api/watchlist", "POST", args.item, args.admin),
    onSuccess: (data) => qc.setQueryData(["watchlist"], data),
  });
}

export function useRemoveWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { ticker: string; admin: string }) =>
      send<WatchlistResponse>(`/api/watchlist/${args.ticker}`, "DELETE", undefined, args.admin),
    onSuccess: (data) => qc.setQueryData(["watchlist"], data),
  });
}

export function useSellWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { ticker: string; percent: number; date?: string; price?: number; admin: string }) =>
      send<WatchlistResponse>(`/api/watchlist/${args.ticker}/sell`, "POST", { percent: args.percent, date: args.date, price: args.price }, args.admin),
    onSuccess: (data) => qc.setQueryData(["watchlist"], data),
  });
}

export function useReverseSell() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { ticker: string; sellIndex: number; admin: string }) =>
      send<WatchlistResponse>(`/api/watchlist/${args.ticker}/sell/${args.sellIndex}`, "DELETE", undefined, args.admin),
    onSuccess: (data) => qc.setQueryData(["watchlist"], data),
  });
}

export function useScreenStatus(universe: string = "sp500") {
  return useQuery({
    queryKey: ["screen", universe],
    queryFn: () => get<ScreenStatus>(`/api/screen?universe=${universe}`),
    refetchInterval: (query) =>
      query.state.data?.state === "running" ? 1500 : false,
  });
}

export function useRunScreen() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { universe?: string; force?: boolean } = {}) => {
      const u = args.universe || "sp500";
      const f = args.force ? "&force=true" : "";
      return send<ScreenStatus>(`/api/screen/run?universe=${u}${f}`, "POST", undefined);
    },
    onSuccess: (data, args) => qc.setQueryData(["screen", args?.universe || "sp500"], data),
  });
}

export async function lookupPrice(ticker: string, date: string, admin: string): Promise<number> {
  const res = await fetch(
    `${BASE}/api/lookup-price?ticker=${encodeURIComponent(ticker)}&date=${date}`,
    { headers: { "X-Admin-Password": admin } },
  );
  if (!res.ok) throw new Error((await res.json()).detail ?? "Lookup failed");
  return (await res.json()).price as number;
}

export async function verifyAdminPassword(admin: string): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/api/admin/verify`, {
      method: "POST",
      headers: { "X-Admin-Password": admin },
    });
    return res.ok;
  } catch {
    return false;
  }
}

export type { WatchlistItem };
