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
from . import db
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
_job: dict = {
    "state": "idle",
    "globalState": "idle",
    "universe": "sp500",
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


def status(universe: str = "sp500") -> dict:
    """Snapshot of the current job, or the cached results if idle."""
    with _lock:
        global_state = _job.get("globalState", "idle")
        active_universe = _job.get("universe")
        
        if _job["state"] == "running" and _job["universe"] == universe:
            results = sorted(_job["results"], key=lambda r: r["score"], reverse=True)
            started = _job["startedAt"]
            elapsed = (time.time() - started) if started else None
            return {
                "state": "running",
                "globalState": global_state,
                "activeUniverse": active_universe,
                "universe": universe,
                "total": _job["total"],
                "done": _job["done"],
                "found": len(results),
                "results": results,
                "elapsed": round(elapsed, 1) if elapsed else None,
                "error": None,
            }

        cached = db.load_cache(universe)
        if cached:
            results = sorted(cached["results"], key=lambda r: r["score"], reverse=True)
            return {
                "state": cached["state"],
                "globalState": global_state,
                "activeUniverse": active_universe,
                "universe": universe,
                "total": cached["total_tickers"],
                "done": cached["done_tickers"],
                "found": len(results),
                "results": results,
                "elapsed": None,
                "error": None,
            }

        return {
            "state": "idle",
            "globalState": global_state,
            "activeUniverse": active_universe,
            "universe": universe,
            "total": 0,
            "done": 0,
            "found": 0,
            "results": [],
            "elapsed": None,
            "error": None,
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
            db.save_cache(universe, _job["results"], "done", _job["total"], _job["done"])
    except Exception as e:  # noqa: BLE001
        with _lock:
            _job["state"] = "error"
            _job["error"] = str(e)
            _job["finishedAt"] = time.time()
            db.save_cache(universe, _job["results"], "error", _job["total"], _job["done"])


def start(settings: HGSettings, universe: str = "sp500", force: bool = False) -> dict:
    """Kick off a scan unless one is already running. Returns current status."""
    tickers = _universe_tickers(universe)
    with _lock:
        if not force:
            cached = db.load_cache(universe)
            if cached and time.time() - cached["updated_at"] < 172800:
                return status(universe)

        if _job["state"] == "running":
            return status(universe)

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
    return status(universe)


def _run_all_sequential(settings: HGSettings, force: bool = False):
    universes = ["sp500", "russell1000", "russell2000"]
    with _lock:
        _job["globalState"] = "running"
    
    for i, uni in enumerate(universes):
        # We manually update _job before starting _run, but _run will also do some updates.
        # It's better to just call start() directly and wait for it.
        start(settings, uni, force=force)
        
        # Wait until the current scan finishes
        while True:
            with _lock:
                if _job["state"] != "running" or _job["universe"] != uni:
                    break
            time.sleep(1)
            
        # Delay before next index to avoid rate limits (unless it's the last one)
        if i < len(universes) - 1:
            time.sleep(180) # 3 minutes
            
    with _lock:
        _job["globalState"] = "idle"


def start_all(settings: HGSettings, force: bool = False) -> dict:
    """Kick off a sequential scan of all universes."""
    with _lock:
        if _job.get("globalState") == "running":
            return status("sp500") # Return any status, the frontend looks at globalState
    
    threading.Thread(target=_run_all_sequential, args=(settings, force), daemon=True).start()
    return status("sp500")
