"""Holygrail API — FastAPI backend for the momentum scanner."""

from __future__ import annotations

import datetime
import os

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import ai, data as datalib, screener, watchlist as wl
from .indicator import HGSettings, compute
from .scan_service import run_scan

app = FastAPI(title="Holygrail API", version="1.0.0")

_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _settings(
    ema_fast: int = 5,
    ema_mid: int = 9,
    ema_slow: int = 21,
    ma50w: int = 50,
    rsi_len: int = 14,
    vol_mult: float = 1.5,
    vol_lookbk: int = 10,
    retest_max: float = 15.0,
    base_min: int = 15,
    w1: float = 0.15,
    w2: float = 0.10,
    w3: float = 0.10,
    w4: float = 0.25,
    w5: float = 0.30,
    w6: float = 0.10,
    partial_thresh: float = 0.35,
    full_thresh: float = 0.70,
) -> HGSettings:
    return HGSettings(
        ema_fast=ema_fast, ema_mid=ema_mid, ema_slow=ema_slow, ma50w=ma50w,
        rsi_len=rsi_len, vol_mult=vol_mult, vol_lookbk=vol_lookbk,
        retest_max=retest_max, base_min=base_min,
        w1=w1, w2=w2, w3=w3, w4=w4, w5=w5, w6=w6,
        partial_thresh=partial_thresh, full_thresh=full_thresh,
    )


def _require_admin(password: str | None):
    correct = os.environ.get("ADMIN_PASSWORD", "holygrail")
    if password != correct:
        raise HTTPException(status_code=401, detail="Incorrect admin password.")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/scan")
def scan(
    ticker: str = Query(..., min_length=1, max_length=12),
    history: str = Query("1Y"),
    ema_fast: int = 5, ema_mid: int = 9, ema_slow: int = 21, ma50w: int = 50,
    rsi_len: int = 14, vol_mult: float = 1.5, vol_lookbk: int = 10,
    retest_max: float = 15.0, base_min: int = 15,
    w1: float = 0.15, w2: float = 0.10, w3: float = 0.10,
    w4: float = 0.25, w5: float = 0.30, w6: float = 0.10,
    partial_thresh: float = 0.35, full_thresh: float = 0.70,
):
    settings = _settings(
        ema_fast, ema_mid, ema_slow, ma50w, rsi_len, vol_mult, vol_lookbk,
        retest_max, base_min, w1, w2, w3, w4, w5, w6, partial_thresh, full_thresh,
    )
    try:
        payload, _res = run_scan(ticker.strip().upper(), history, settings)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Failed to load {ticker}: {e}")
    return payload


@app.get("/api/scan/{ticker}/ai")
def scan_ai(ticker: str, full_thresh: float = 0.70, partial_thresh: float = 0.35, retest_max: float = 15.0):
    ticker = ticker.strip().upper()
    settings = _settings(retest_max=retest_max, partial_thresh=partial_thresh, full_thresh=full_thresh)
    try:
        ohlcv = datalib.fetch_weekly(ticker, period="10y")
        spx = datalib.fetch_spx_weekly(period="10y")
        name = datalib.resolve_name(ticker)
        news = datalib.fetch_news(ticker)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Failed to load {ticker}: {e}")
    res = compute(ohlcv, spx_close=spx if not spx.empty else None, settings=settings)
    tech_html, tech_src = ai.technical_summary(ticker, name, res, settings)
    fund_html, fund_src = ai.fundamental_summary(ticker, name)
    narr_html, narr_src = ai.catalyst_narrative(ticker, name, news)
    return {
        "technical": {"html": tech_html, "source": tech_src},
        "fundamental": {"html": fund_html, "source": fund_src},
        "narrative": {"html": narr_html, "source": narr_src},
    }


# Guide case studies (ticker + date window from the original app).
GUIDE_CASES = [
    {"ticker": "ARM", "start": "2025-08-01", "end": "2026-06-01"},
    {"ticker": "AMD", "start": "2025-01-01", "end": "2026-06-19"},
    {"ticker": "ADBE", "start": "2024-10-01", "end": "2025-08-01"},
]


@app.get("/api/guide/{ticker}")
def guide_case(ticker: str, start: str, end: str):
    ticker = ticker.strip().upper()
    settings = _settings()
    try:
        ohlcv = datalib.fetch_weekly(ticker, period="10y")
        spx = datalib.fetch_spx_weekly(period="10y")
        name = datalib.resolve_name(ticker)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Failed to load {ticker}: {e}")
    res = compute(ohlcv, spx_close=spx if not spx.empty else None, settings=settings)
    # Window-filter via serialize with a manual slice.
    from .scan_service import serialize_scan

    res.df = res.df.loc[start:end]
    payload = serialize_scan(ticker, name, res, history="5Y")
    # 5Y filter may clip the historical window; re-slice candles by string compare.
    for key in ("candles", "cloud", "ma50w", "ema5", "ema9", "ema21"):
        payload[key] = [p for p in payload[key] if start <= p["time"] <= end]
    for mkey in payload["markers"]:
        payload["markers"][mkey] = [p for p in payload["markers"][mkey] if start <= p["time"] <= end]
    return payload


@app.post("/api/screen/run")
def screen_run(
    retest_max: float = 15.0,
    base_min: int = 15,
    partial_thresh: float = 0.35,
    full_thresh: float = 0.70,
):
    settings = _settings(
        retest_max=retest_max, base_min=base_min,
        partial_thresh=partial_thresh, full_thresh=full_thresh,
    )
    return screener.start(settings)


@app.get("/api/screen")
def screen_status():
    return screener.status()


@app.get("/api/watchlist")
def get_watchlist():
    items = wl.load()
    return {"items": wl.with_live_prices(items), "githubEnabled": wl.github_enabled()}


class WatchlistItem(BaseModel):
    ticker: str
    date_added: str
    price_added: float
    verdict: str = "WATCH"
    commentary: str = ""


@app.post("/api/watchlist")
def add_watchlist(item: WatchlistItem, x_admin_password: str | None = Header(default=None)):
    _require_admin(x_admin_password)
    if item.price_added <= 0:
        raise HTTPException(status_code=400, detail="Price must be > 0.")
    items = wl.load()
    ticker = item.ticker.strip().upper()
    items = [x for x in items if x.get("ticker") != ticker]
    items.append(
        {
            "ticker": ticker,
            "date_added": item.date_added,
            "price_added": float(item.price_added),
            "verdict": item.verdict,
            "commentary": item.commentary,
        }
    )
    if not wl.save(items):
        raise HTTPException(status_code=502, detail="Failed to persist watchlist.")
    return {"items": wl.with_live_prices(items), "githubEnabled": wl.github_enabled()}


@app.delete("/api/watchlist/{ticker}")
def remove_watchlist(ticker: str, x_admin_password: str | None = Header(default=None)):
    _require_admin(x_admin_password)
    ticker = ticker.strip().upper()
    items = [x for x in wl.load() if x.get("ticker") != ticker]
    if not wl.save(items):
        raise HTTPException(status_code=502, detail="Failed to persist watchlist.")
    return {"items": wl.with_live_prices(items), "githubEnabled": wl.github_enabled()}


@app.get("/api/lookup-price")
def lookup_price(ticker: str, date: str, x_admin_password: str | None = Header(default=None)):
    _require_admin(x_admin_password)
    import yfinance as yf

    ticker = ticker.strip().upper()
    try:
        start = datetime.datetime.strptime(date, "%Y-%m-%d")
        end = start + datetime.timedelta(days=7)
        hist = yf.Ticker(ticker).history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        if hist.empty:
            raise HTTPException(status_code=404, detail="No trading data for this date.")
        return {"price": float(hist["Close"].iloc[0])}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lookup failed: {e}")
