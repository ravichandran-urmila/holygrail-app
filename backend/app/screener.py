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


_lock = threading.Lock()
_job: dict = {
    "state": "idle",          # idle | running | done | error
    "total": 0,
    "done": 0,
    "results": [],
    "startedAt": None,
    "finishedAt": None,
    "error": None,
}


def _reset(total: int) -> None:
    with _lock:
        _job.update(
            state="running",
            total=total,
            done=0,
            results=[],
            startedAt=time.time(),
            finishedAt=None,
            error=None,
        )


def status() -> dict:
    """Snapshot of the current job, results sorted by score (desc)."""
    with _lock:
        results = sorted(_job["results"], key=lambda r: r["score"], reverse=True)
        started = _job["startedAt"]
        finished = _job["finishedAt"]
        elapsed = (finished or time.time()) - started if started else None
        return {
            "state": _job["state"],
            "total": _job["total"],
            "done": _job["done"],
            "found": len(results),
            "results": results,
            "elapsed": round(elapsed, 1) if elapsed is not None else None,
            "error": _job["error"],
        }


def _score_one(ticker: str, spx: pd.Series, settings: HGSettings) -> dict | None:
    ohlcv = datalib.fetch_weekly(ticker, period="10y")
    if ohlcv is None or len(ohlcv) < settings.ma50w + 2:
        return None
    res = compute(ohlcv, spx_close=spx if not spx.empty else None, settings=settings)
    sm = res.summary
    last = res.df.iloc[-1]
    return {
        "ticker": ticker,
        "score": _num(sm["weighted_score"]) or 0.0,
        "verdict": sm["verdict"],
        "fullSetup": bool(sm["full_setup"]),
        "partialSetup": bool(sm["partial_setup"]),
        "lastClose": _num(sm["last_close"]),
        "entryLow": _num(sm["entry_price_low"]),
        "entryHigh": _num(sm["entry_price_high"]),
        "mansfieldRs": _num(last.get("mansfield_rs")),
        "pctAbove50w": _num(last.get("pct_above_50w")),
        "rsi14": _num(last.get("rsi14")),
    }


def _run(settings: HGSettings) -> None:
    try:
        spx = datalib.fetch_spx_weekly(period="10y")
    except Exception:  # noqa: BLE001
        spx = pd.Series(dtype=float)

    def worker(tkr: str):
        try:
            return _score_one(tkr, spx, settings)
        except Exception:  # noqa: BLE001 — skip throttled/failed tickers
            return None

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(worker, t): t for t in SP500}
            for fut in as_completed(futures):
                row = fut.result()
                with _lock:
                    _job["done"] += 1
                    if row is not None:
                        _job["results"].append(row)
        with _lock:
            _job["state"] = "done"
            _job["finishedAt"] = time.time()
    except Exception as e:  # noqa: BLE001
        with _lock:
            _job["state"] = "error"
            _job["error"] = str(e)
            _job["finishedAt"] = time.time()


def start(settings: HGSettings) -> dict:
    """Kick off a scan unless one is already running. Returns current status."""
    with _lock:
        if _job["state"] == "running":
            already = True
        else:
            already = False
    if already:
        return status()
    _reset(len(SP500))
    threading.Thread(target=_run, args=(settings,), daemon=True).start()
    return status()
