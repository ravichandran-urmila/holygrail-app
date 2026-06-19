"""
Holy Grail - Green Cloud Retest Scanner
=======================================
Faithful Python port of the Pine Script v6 indicator (`core`).

The original runs on TradingView WEEKLY charts. This module reproduces the
exact rule logic, weighted score and dashboard values so they can be rendered
outside TradingView (no TradingView API needed - all math is portable).

All stateful logic (`var` series, crossovers, "weeks since" counters) is
replicated bar-by-bar exactly as Pine evaluates it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Settings - mirror the Pine `input.*` defaults
# ---------------------------------------------------------------------------
@dataclass
class HGSettings:
    ema_fast: int = 5
    ema_mid: int = 9
    ema_slow: int = 21
    ma50w: int = 50
    rsi_len: int = 14
    vol_mult: float = 1.5
    vol_lookbk: int = 10
    retest_max: float = 10.0
    base_min: int = 15
    rs_window: int = 8

    # Rule weights
    w1: float = 0.15  # Retest
    w2: float = 0.10  # Breakout
    w3: float = 0.10  # Base length
    w4: float = 0.25  # Green cloud
    w5: float = 0.30  # Mansfield RS
    w6: float = 0.10  # RSI > 50

    partial_thresh: float = 0.35
    full_thresh: float = 0.70

    @property
    def total_weight(self) -> float:
        return self.w1 + self.w2 + self.w3 + self.w4 + self.w5 + self.w6


# ---------------------------------------------------------------------------
# TA helpers (match Pine's ta.* semantics)
# ---------------------------------------------------------------------------
def ema(series: pd.Series, length: int) -> pd.Series:
    # Pine ta.ema seeds with an SMA then applies the EMA multiplier.
    # pandas ewm(adjust=False) matches Pine closely for typical history lengths.
    return series.ewm(span=length, adjust=False).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length, min_periods=length).mean()


def rsi(series: pd.Series, length: int) -> pd.Series:
    # Wilder's RSI (RMA), matching Pine ta.rsi.
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    alpha = 1.0 / length
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    out[avg_loss == 0] = 100.0
    return out


def crossover(a: pd.Series, b: pd.Series) -> pd.Series:
    """Pine ta.crossover(a, b): a crosses above b this bar."""
    a_prev, b_prev = a.shift(1), b.shift(1)
    return (a > b) & (a_prev <= b_prev)


def crossunder(a: pd.Series, b: pd.Series) -> pd.Series:
    a_prev, b_prev = a.shift(1), b.shift(1)
    return (a < b) & (a_prev >= b_prev)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------
@dataclass
class HGResult:
    df: pd.DataFrame                      # full series (one row per weekly bar)
    settings: HGSettings
    dashboard: list = field(default_factory=list)   # last-bar dashboard rows
    summary: dict = field(default_factory=dict)     # convenience scalars


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------
def compute(
    ohlcv: pd.DataFrame,
    spx_close: Optional[pd.Series] = None,
    settings: Optional[HGSettings] = None,
) -> HGResult:
    """
    Parameters
    ----------
    ohlcv : DataFrame indexed by date with columns
            ['open', 'high', 'low', 'close', 'volume'] at WEEKLY resolution.
    spx_close : weekly SPX close aligned (or alignable) to `ohlcv.index`.
                Used for Rule 5 (Mansfield RS). If None, Rule 5 is skipped.
    """
    s = settings or HGSettings()
    df = ohlcv.copy()
    df.columns = [c.lower() for c in df.columns]

    close, open_, volume = df["close"], df["open"], df["volume"]

    # --- Core calcs ---------------------------------------------------------
    df["ema5"] = ema(close, s.ema_fast)
    df["ema9"] = ema(close, s.ema_mid)
    df["ema21"] = ema(close, s.ema_slow)
    df["ma50w"] = sma(close, s.ma50w)
    df["rsi14"] = rsi(close, s.rsi_len)

    vol_avg = sma(volume, s.vol_lookbk)
    df["vol_ratio"] = volume / vol_avg

    # --- Rule 1: Retest -----------------------------------------------------
    df["pct_above_50w"] = (close - df["ma50w"]) / df["ma50w"] * 100.0
    df["rule1_retest"] = (df["pct_above_50w"] >= 0) & (df["pct_above_50w"] <= s.retest_max)

    crossed_above = crossover(close, df["ma50w"])
    crossed_under = crossunder(close, df["ma50w"])
    df["crossed_above_50w"] = crossed_above

    # --- Stateful loop (Rules 2 & 3 and RS-green counter) -------------------
    n = len(df)
    weeks_since_breakout = np.full(n, np.nan)
    breakout_valid_vol = np.zeros(n, dtype=bool)
    weeks_below_50w = np.zeros(n, dtype=int)
    captured_base = np.zeros(n, dtype=int)

    vr = df["vol_ratio"].to_numpy()
    ca = crossed_above.to_numpy()
    below = (close < df["ma50w"]).to_numpy()

    prev_wsb = np.nan      # weeks_since_breakout (previous bar value)
    prev_bvv = False       # breakout_valid_vol
    prev_below = 0         # weeks_below_50w previous value
    prev_base = 0          # captured_base_length previous value

    for i in range(n):
        # Rule 2 state
        if ca[i]:
            wsb = 0.0
            bvv = (vr[i] >= s.vol_mult) if not np.isnan(vr[i]) else False
        else:
            bvv = prev_bvv
            wsb = (prev_wsb + 1) if not np.isnan(prev_wsb) else np.nan

        # Rule 3 state  (Pine: if close<ma else if crossover)
        if below[i]:
            wb = prev_below + 1
            cb = prev_base
        elif ca[i]:
            cb = prev_below           # weeks_below_50w[1] == previous bar value
            wb = 0
        else:
            wb = prev_below
            cb = prev_base

        weeks_since_breakout[i] = wsb
        breakout_valid_vol[i] = bvv
        weeks_below_50w[i] = wb
        captured_base[i] = cb

        prev_wsb, prev_bvv, prev_below, prev_base = wsb, bvv, wb, cb

    df["weeks_since_breakout"] = weeks_since_breakout
    df["captured_base_length"] = captured_base

    df["rule2_breakout"] = (
        (~np.isnan(weeks_since_breakout))
        & (weeks_since_breakout >= 1)
        & breakout_valid_vol
    )
    df["rule3_base"] = df["captured_base_length"] >= s.base_min

    # --- Rule 4: Green cloud birth -----------------------------------------
    ema5_cross_ema9 = crossover(df["ema5"], df["ema9"])
    recent_cross = ema5_cross_ema9 | ema5_cross_ema9.shift(1).fillna(False) | ema5_cross_ema9.shift(2).fillna(False)
    ema9_near_21 = (df["ema9"] - df["ema21"]).abs() / df["ema21"] * 100 < 2.0
    ema5_near_9 = (df["ema5"] - df["ema9"]).abs() / df["ema9"] * 100 < 2.0
    compressed = ema5_near_9 & ema9_near_21
    price_above = (close > df["ema5"]) & (close > df["ema9"]) & (close > df["ema21"])
    green_candle = close > open_
    df["rule4_green_cloud"] = recent_cross & compressed & price_above & green_candle

    # --- Rule 5: Mansfield Relative Strength --------------------------------
    if spx_close is not None:
        spx = spx_close.reindex(df.index).ffill()
        raw_rs = close / spx
        rs_sma = sma(raw_rs, 52)
        mansfield = np.where(rs_sma != 0, (raw_rs / rs_sma - 1) * 10, 0.0)
        df["mansfield_rs"] = mansfield
        df["rule5_mansfield"] = df["mansfield_rs"] > 0

        rs_cross = crossover(df["mansfield_rs"], pd.Series(0.0, index=df.index))
        weeks_green = np.zeros(n, dtype=int)
        prev_green = 0
        mr = df["mansfield_rs"].to_numpy()
        rc = rs_cross.to_numpy()
        for i in range(n):
            if rc[i]:
                wg = 1
            elif mr[i] > 0:
                wg = prev_green + 1
            else:
                wg = 0
            weeks_green[i] = wg
            prev_green = wg
        df["weeks_since_rs_green"] = weeks_green
    else:
        df["mansfield_rs"] = np.nan
        df["rule5_mansfield"] = False
        df["weeks_since_rs_green"] = 0

    # --- Rule 6: RSI shift --------------------------------------------------
    df["rule6_rsi"] = df["rsi14"] > 50

    # --- Scoring ------------------------------------------------------------
    df["weighted_score"] = (
        df["rule1_retest"] * s.w1
        + df["rule2_breakout"] * s.w2
        + df["rule3_base"] * s.w3
        + df["rule4_green_cloud"] * s.w4
        + df["rule5_mansfield"] * s.w5
        + df["rule6_rsi"] * s.w6
    )
    df["full_setup"] = (s.total_weight > 0) & (df["weighted_score"] >= s.full_thresh)
    df["partial_setup"] = (
        df["rule1_retest"]
        & (~df["full_setup"])
        & (df["weighted_score"] >= s.partial_thresh)
    )
    df["stop_trigger"] = crossed_under

    # --- Dashboard (last bar) ----------------------------------------------
    last = df.iloc[-1]
    ws = float(last["weighted_score"])

    def status(passed, w):
        return (f"PASS ({w:g})" if passed else "FAIL")

    dashboard = [
        ("1 · Retest Zone", status(last["rule1_retest"], s.w1),
         f"{last['pct_above_50w']:.2f}% above 50WMA (${last['ma50w']:.2f})", bool(last["rule1_retest"])),
        ("2 · Breakout+Vol", status(last["rule2_breakout"], s.w2),
         f"{_fmt_int(last['weeks_since_breakout'])} wks ago | Vol {last['vol_ratio']:.2f}x", bool(last["rule2_breakout"])),
        ("3 · Base Length", status(last["rule3_base"], s.w3),
         f"{int(last['captured_base_length'])} wks (min {s.base_min})", bool(last["rule3_base"])),
        ("4 · Green Cloud", status(last["rule4_green_cloud"], s.w4),
         f"EMA5 {last['ema5']:.2f}  EMA9 {last['ema9']:.2f}  EMA21 {last['ema21']:.2f}", bool(last["rule4_green_cloud"])),
        ("5 · Mansfield RS", status(last["rule5_mansfield"], s.w5),
         f"RS: {_fmt_f(last['mansfield_rs'])} | {int(last['weeks_since_rs_green'])} wks green", bool(last["rule5_mansfield"])),
        ("6 · RSI > 50", status(last["rule6_rsi"], s.w6),
         f"RSI: {last['rsi14']:.1f}", bool(last["rule6_rsi"])),
    ]

    if ws >= s.full_thresh:
        verdict = "COMPLETE SETUP"
    elif ws >= s.partial_thresh:
        verdict = "WATCHING"
    else:
        verdict = "NO SETUP"

    entry_price = last["ma50w"] * 1.005
    stop_price = last["ma50w"] * 0.995

    summary = {
        "weighted_score": ws,
        "total_weight": s.total_weight,
        "verdict": verdict,
        "full_setup": bool(last["full_setup"]),
        "partial_setup": bool(last["partial_setup"]),
        "entry_price": float(entry_price),
        "stop_price": float(stop_price),
        "last_close": float(last["close"]),
        "last_date": df.index[-1],
    }

    return HGResult(df=df, settings=s, dashboard=dashboard, summary=summary)


def _fmt_int(v) -> str:
    return "n/a" if (v is None or (isinstance(v, float) and np.isnan(v))) else str(int(v))


def _fmt_f(v) -> str:
    return "n/a" if (v is None or (isinstance(v, float) and np.isnan(v))) else f"{v:.2f}"
