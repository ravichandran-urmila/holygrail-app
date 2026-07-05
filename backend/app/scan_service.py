"""Turns raw weekly data + indicator output into a chart-ready JSON payload."""

from __future__ import annotations

import datetime
import math
from typing import Optional

import numpy as np
import pandas as pd

from . import data as datalib
from .indicator import HGSettings, HGResult, compute


HISTORY_DAYS = {
    "3M": 90,
    "6M": 180,
    "YTD": None,  # special-cased
    "1Y": 365,
    "2Y": 2 * 365,
    "5Y": 5 * 365,
}


def _num(v) -> Optional[float]:
    """JSON-safe float (None for NaN/inf)."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _line(df: pd.DataFrame, col: str) -> list[dict]:
    out = []
    for ts, val in df[col].items():
        v = _num(val)
        if v is not None:
            out.append({"time": ts.strftime("%Y-%m-%d"), "value": v})
    return out


def _filter_by_history(df: pd.DataFrame, history: str) -> pd.DataFrame:
    now = datetime.datetime.now()
    if history == "YTD":
        start = datetime.datetime(now.year, 1, 1)
    else:
        days = HISTORY_DAYS.get(history, 365)
        start = now - datetime.timedelta(days=days)
    return df[df.index >= start]


def serialize_scan(
    ticker: str,
    name: str,
    res: HGResult,
    history: str = "1Y",
) -> dict:
    df = res.df
    sm = res.summary
    s = res.settings
    view = _filter_by_history(df, history)

    candles = [
        {
            "time": ts.strftime("%Y-%m-%d"),
            "open": _num(row["open"]),
            "high": _num(row["high"]),
            "low": _num(row["low"]),
            "close": _num(row["close"]),
            "volume": _num(row["volume"]),
        }
        for ts, row in view.iterrows()
    ]

    # EMA cloud: per-bar upper/lower + colour flag for the band fill.
    cloud = []
    for ts, row in view.iterrows():
        e5, e21 = _num(row["ema5"]), _num(row["ema21"])
        if e5 is None or e21 is None:
            continue
        cloud.append(
            {
                "time": ts.strftime("%Y-%m-%d"),
                "upper": max(e5, e21),
                "lower": min(e5, e21),
                "green": bool(e5 >= e21),
            }
        )

    def _markers(mask_col: str) -> list[dict]:
        if mask_col not in view.columns:
            return []
        sub = view[view[mask_col]]
        return [
            {"time": ts.strftime("%Y-%m-%d"), "low": _num(r["low"]), "close": _num(r["close"])}
            for ts, r in sub.iterrows()
        ]

    # Per-bar table (most recent first) for the Data tab.
    table = []
    for ts, row in view.iloc[::-1].iterrows():
        table.append(
            {
                "date": ts.strftime("%Y-%m-%d"),
                "open": _num(row["open"]),
                "high": _num(row["high"]),
                "low": _num(row["low"]),
                "close": _num(row["close"]),
                "volume": _num(row["volume"]),
                "ma50w": _num(row.get("ma50w")),
                "ema5": _num(row.get("ema5")),
                "ema9": _num(row.get("ema9")),
                "ema21": _num(row.get("ema21")),
                "rsi14": _num(row.get("rsi14")),
                "pctAbove50w": _num(row.get("pct_above_50w")),
                "mansfieldRs": _num(row.get("mansfield_rs")),
                "weightedScore": _num(row.get("weighted_score")),
                "fullSetup": bool(row.get("full_setup", False)),
                "partialSetup": bool(row.get("partial_setup", False)),
                "hrr": bool(row.get("blue_square", False)),
            }
        )

    dashboard = [
        {"rule": rule, "status": status, "value": value, "passed": bool(passed)}
        for rule, status, value, passed in res.dashboard
    ]

    summary = {
        "weightedScore": _num(sm["weighted_score"]),
        "totalWeight": _num(sm["total_weight"]),
        "verdict": sm["verdict"],
        "fullSetup": bool(sm["full_setup"]),
        "partialSetup": bool(sm["partial_setup"]),
        "entryPriceLow": _num(sm["entry_price_low"]),
        "entryPriceHigh": _num(sm["entry_price_high"]),
        "stopPrice": _num(sm["stop_price"]),
        "lastClose": _num(sm["last_close"]),
        "lastDate": sm["last_date"].strftime("%Y-%m-%d") if sm["last_date"] is not None else None,
        "lastHgDate": sm["last_hg_date"].strftime("%Y-%m-%d") if sm["last_hg_date"] is not None else None,
        "lastHgEntry": _num(sm["last_hg_entry"]),
        "lastHgGainPct": _num(sm["last_hg_gain_pct"]),
    }

    return {
        "ticker": ticker.upper(),
        "name": name,
        "history": history,
        "summary": summary,
        "candles": candles,
        "cloud": cloud,
        "ma50w": _line(view, "ma50w"),
        "ema5": _line(view, "ema5"),
        "ema9": _line(view, "ema9"),
        "ema21": _line(view, "ema21"),
        "markers": {
            "fullSetup": _markers("full_setup"),
            "partial": _markers("partial_setup"),
            "hrr": _markers("blue_square"),
        },
        "dashboard": dashboard,
        "table": table,
        "settings": {
            "retestMax": s.retest_max,
            "fullThresh": s.full_thresh,
            "partialThresh": s.partial_thresh,
        },
    }


def run_scan(ticker: str, history: str, settings: HGSettings) -> dict:
    ohlcv = datalib.fetch_weekly(ticker, period="10y")
    spx = datalib.fetch_spx_weekly(period="10y")
    name = datalib.resolve_name(ticker)
    res = compute(ohlcv, spx_close=spx if not spx.empty else None, settings=settings)
    payload = serialize_scan(ticker, name, res, history)
    payload["insufficientData"] = len(ohlcv) < settings.ma50w + 2
    return payload, res
