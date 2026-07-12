"""S&P 500 Holy Grail screener.

Runs the same validated `compute()` engine across the whole universe in a
background thread (so the HTTP request returns immediately) and exposes
live progress + streaming results via an in-memory job. On-demand: a scan
is kicked off by POST /api/screen/run and polled via GET /api/screen.
"""

from __future__ import annotations

import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from . import data as datalib
from .indicator import HGSettings, compute
from .sp500 import SP500

MAX_WORKERS = 8


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


_lock = threading.RLock()
_completed_scans: dict[str, tuple[float, list]] = {}
_job: dict = {
    "state": "idle",          # idle | running | done | error
    "universe": "sp500",      # sp500 | russell2000
    "total": 0,
    "done": 0,
    "results": [],
    "startedAt": None,
    "finishedAt": None,
    "error": None,
}


def _universe_tickers(universe: str) -> list[str]:
    if universe == "russell2000":
        from .russell2000 import RUSSELL2000
        return RUSSELL2000
    if universe == "russell1000":
        from .russell1000 import RUSSELL1000
        return RUSSELL1000
    return SP500


def status() -> dict:
    """Snapshot of the current job, results sorted by score (desc)."""
    with _lock:
        results = sorted(_job["results"], key=lambda r: r["score"], reverse=True)
        started = _job["startedAt"]
        finished = _job["finishedAt"]
        elapsed = (finished or time.time()) - started if started else None
        return {
            "state": _job["state"],
            "universe": _job.get("universe", "sp500"),
            "total": _job["total"],
            "done": _job["done"],
            "found": len(results),
            "results": results,
            "elapsed": round(elapsed, 1) if elapsed is not None else None,
            "error": _job["error"],
        }


def _score_one(ticker: str, spx: pd.Series, settings: HGSettings) -> dict | None:
    ohlcv = datalib.fetch_weekly(ticker, period="2y")
    if ohlcv is None or len(ohlcv) < settings.ma50w + 2:
        return None
    
    # Early filter: skip tickers trading below the 50WMA
    close = ohlcv["close"]
    ma50w = close.rolling(window=settings.ma50w).mean()
    last_close = close.iloc[-1]
    last_ma50 = ma50w.iloc[-1]
    if pd.isna(last_ma50) or last_close < last_ma50:
        return None

    res = compute(ohlcv, spx_close=spx if not spx.empty else None, settings=settings)
    sm = res.summary
    last = res.df.iloc[-1]

    # Find weeks since last complete setup
    full_setup_series = res.df["full_setup"]
    true_indices = full_setup_series.values.nonzero()[0]
    n = len(res.df)
    if len(true_indices) > 0:
        weeks_since_last_full = int((n - 1) - true_indices[-1])
    else:
        weeks_since_last_full = None

    return {
        "ticker": ticker,
        "score": _num(sm["weighted_score"]) or 0.0,
        "verdict": sm["verdict"],
        "fullSetup": bool(sm["full_setup"]),
        "partialSetup": bool(sm["partial_setup"]),
        "weeksSinceLastFull": weeks_since_last_full,
        "lastClose": _num(sm["last_close"]),
        "entryLow": _num(sm["entry_price_low"]),
        "entryHigh": _num(sm["entry_price_high"]),
        "mansfieldRs": _num(last.get("mansfield_rs")),
        "pctAbove50w": _num(last.get("pct_above_50w")),
        "rsi14": _num(last.get("rsi14")),
    }


def _run(settings: HGSettings, tickers: list[str], universe: str) -> None:
    try:
        spx = datalib.fetch_spx_weekly(period="2y")
    except Exception:  # noqa: BLE001
        spx = pd.Series(dtype=float)

    def worker(tkr: str):
        try:
            return _score_one(tkr, spx, settings)
        except Exception:  # noqa: BLE001 — skip throttled/failed tickers
            return None

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(worker, t): t for t in tickers}
            for fut in as_completed(futures):
                row = fut.result()
                with _lock:
                    _job["done"] += 1
                    if row is not None:
                        _job["results"].append(row)
        with _lock:
            _job["state"] = "done"
            _job["finishedAt"] = time.time()
            # Cache completed scan results for this universe
            _completed_scans[universe] = (time.time(), list(_job["results"]))
    except Exception as e:  # noqa: BLE001
        with _lock:
            _job["state"] = "error"
            _job["error"] = str(e)
            _job["finishedAt"] = time.time()


def start(settings: HGSettings, universe: str = "sp500") -> dict:
    """Kick off a scan unless one is already running. Returns current status.

    Only one scan runs at a time. If a scan is already in flight (for any
    universe) the call is a no-op that returns the live progress. The state
    check and the transition to "running" happen under a single lock, so two
    near-simultaneous clicks can't both spawn a scan and clobber each other.
    """
    tickers = _universe_tickers(universe)
    with _lock:
        # Serve a scan completed within the last hour from cache.
        if universe in _completed_scans:
            completed_at, cached_results = _completed_scans[universe]
            if time.time() - completed_at < 3600:
                _job.update(
                    state="done",
                    universe=universe,
                    total=len(tickers),
                    done=len(tickers),
                    results=cached_results,
                    startedAt=completed_at - 10,
                    finishedAt=completed_at,
                    error=None,
                )
                return status()

        # Single-flight: a scan is already running — don't start another.
        if _job["state"] == "running":
            return status()

        # Claim the job before releasing the lock so no other caller can start one.
        _job.update(
            state="running",
            universe=universe,
            total=len(tickers),
            done=0,
            results=[],
            startedAt=time.time(),
            finishedAt=None,
            error=None,
        )

    threading.Thread(target=_run, args=(settings, tickers, universe), daemon=True).start()
    return status()
