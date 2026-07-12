"""Holygrail API — FastAPI backend for the momentum scanner."""

from __future__ import annotations

import datetime
import os
import random
import secrets
import smtplib
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import ai, data as datalib, screener, watchlist as wl, db, scheduler
from .indicator import HGSettings, compute
from .scan_service import run_scan

app = FastAPI(title="Holygrail API", version="1.0.0")

_cors_env = os.environ.get("CORS_ORIGINS", "*")
_origins = ["*"] if _cors_env == "*" else [o.strip() for o in _cors_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_cors_env != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    db.init_db()
    scheduler.start_scheduler()


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


class AdminAuthStore:
    def __init__(self):
        self.active_pin: str | None = None
        self.pin_expires_at: float = 0.0
        self.sessions: dict[str, float] = {}

auth_store = AdminAuthStore()


def _send_email_async(subject: str, body: str, recipient: str):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    
    if not smtp_host or not smtp_port or not smtp_user or not smtp_pass:
        print("[AdminAuth] SMTP environment variables not fully configured. Email skipped.")
        return
        
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        
        port = int(smtp_port)
        if port == 465:
            with smtplib.SMTP_SSL(smtp_host, port) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, recipient, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, recipient, msg.as_string())
        print(f"[AdminAuth] PIN email sent successfully to {recipient}.")
    except Exception as e:
        print(f"[AdminAuth] Failed to send email: {e}")


def send_email_in_background(subject: str, body: str, recipient: str):
    thread = threading.Thread(target=_send_email_async, args=(subject, body, recipient))
    thread.daemon = True
    thread.start()


class VerifyPinRequest(BaseModel):
    pin: str


def _require_admin(password: str | None):
    if not password:
        raise HTTPException(status_code=401, detail="Admin authorization required.")
        
    now = time.time()
    # Clean up expired sessions
    auth_store.sessions = {t: exp for t, exp in auth_store.sessions.items() if exp > now}
    
    if password in auth_store.sessions:
        return
        
    correct = os.environ.get("ADMIN_PASSWORD", "holygrail")
    admin_email = os.environ.get("ADMIN_EMAIL")
    
    # Dev mode: allow static password if admin_email (production email setting) is not configured
    if not admin_email and password == correct:
        return
        
    raise HTTPException(status_code=401, detail="Incorrect admin credentials or session expired.")


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
    universe: str = "sp500",
    force: bool = False,
    retest_max: float = 15.0,
    base_min: int = 15,
    partial_thresh: float = 0.35,
    full_thresh: float = 0.70,
):
    settings = _settings(
        retest_max=retest_max, base_min=base_min,
        partial_thresh=partial_thresh, full_thresh=full_thresh,
    )
    return screener.start(settings, universe, force=force)


@app.post("/api/screen/run-all")
def screen_run_all(
    force: bool = True,
    retest_max: float = 15.0,
    base_min: int = 15,
    partial_thresh: float = 0.35,
    full_thresh: float = 0.70,
):
    settings = _settings(
        retest_max=retest_max, base_min=base_min,
        partial_thresh=partial_thresh, full_thresh=full_thresh,
    )
    return screener.start_all(settings, force=force)


@app.get("/api/screen")
def screen_status(universe: str = "sp500"):
    return screener.status(universe)


@app.get("/api/watchlist")
def get_watchlist():
    items = wl.load()
    return {"items": wl.with_live_prices(items), "githubEnabled": wl.github_enabled()}


class WatchlistItem(BaseModel):
    ticker: str
    date_added: str
    price_added: float
    price_target: float | None = None
    options: str | None = ""
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
            "price_target": float(item.price_target) if item.price_target is not None else None,
            "options": item.options,
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


class SellRequest(BaseModel):
    percent: float
    price: float | None = None
    date: str | None = None


@app.post("/api/watchlist/{ticker}/sell")
def sell_watchlist(ticker: str, req: SellRequest, x_admin_password: str | None = Header(default=None)):
    _require_admin(x_admin_password)
    if not (0 < req.percent <= 100):
        raise HTTPException(status_code=400, detail="Percent must be between 0 and 100.")
    ticker = ticker.strip().upper()
    items = wl.load()
    
    target = None
    for item in items:
        if item.get("ticker") == ticker and item.get("status", "open") == "open":
            target = item
            break
            
    if not target:
        raise HTTPException(status_code=404, detail="Open position not found.")
        
    current_price = req.price
    if current_price is None:
        current_price = datalib.fetch_last_close(ticker)
        if current_price is None:
            raise HTTPException(status_code=500, detail="Failed to fetch current price automatically.")
            
    if current_price <= 0:
        raise HTTPException(status_code=400, detail="Price must be > 0.")
        
    sells = target.get("sells", [])
    current_size = target.get("position_size", 100)
    sell_percent = min(req.percent, current_size)
    
    sells.append({
        "date": req.date if req.date else datetime.date.today().isoformat(),
        "percent": sell_percent,
        "price": current_price
    })
    
    new_size = current_size - sell_percent
    target["sells"] = sells
    target["position_size"] = new_size
    if new_size <= 0:
        target["status"] = "closed"
        
    if not wl.save(items):
        raise HTTPException(status_code=502, detail="Failed to persist watchlist.")
    return {"items": wl.with_live_prices(items), "githubEnabled": wl.github_enabled()}


@app.delete("/api/watchlist/{ticker}/sell/{sell_index}")
def reverse_sell(ticker: str, sell_index: int, x_admin_password: str | None = Header(default=None)):
    _require_admin(x_admin_password)
    ticker = ticker.strip().upper()
    items = wl.load()
    
    target = None
    for item in items:
        if item.get("ticker") == ticker:
            target = item
            break
            
    if not target:
        raise HTTPException(status_code=404, detail="Position not found.")
        
    sells = target.get("sells", [])
    if not (0 <= sell_index < len(sells)):
        raise HTTPException(status_code=400, detail="Sell record not found.")
        
    # Remove the sell and refund the position size
    removed_sell = sells.pop(sell_index)
    target["position_size"] = target.get("position_size", 0) + removed_sell.get("percent", 0)
    
    # If the position size is now > 0, make sure status is open
    if target["position_size"] > 0:
        target["status"] = "open"
        
    target["sells"] = sells
    
    if not wl.save(items):
        raise HTTPException(status_code=502, detail="Failed to persist watchlist.")
    return {"items": wl.with_live_prices(items), "githubEnabled": wl.github_enabled()}


@app.post("/api/admin/verify")
def verify_admin(x_admin_password: str | None = Header(default=None)):
    _require_admin(x_admin_password)
    return {"status": "ok"}


@app.post("/api/admin/request-pin")
def request_pin():
    pin = f"{random.randint(100000, 999999)}"
    auth_store.active_pin = pin
    auth_store.pin_expires_at = time.time() + 300  # 5 minutes
    
    print(f"\n========================================\n[AdminAuth] GENERATED TEMPORARY PIN: {pin}\n========================================\n")
    
    admin_email = os.environ.get("ADMIN_EMAIL")
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_configured = bool(smtp_host and admin_email)
    
    if admin_email:
        subject = "Holy Grail Admin PIN"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #0d1117; color: #e6edf3; padding: 24px;">
                <div style="max-width: 500px; margin: 0 auto; border: 1px solid #30363d; border-radius: 12px; padding: 24px; background-color: #161b22;">
                    <h2 style="color: #58a6ff; margin-top: 0;">Holy Grail Admin</h2>
                    <p>Your temporary Holy Grail Admin login PIN is:</p>
                    <div style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #58a6ff; padding: 12px; border-radius: 8px; background-color: #21262d; text-align: center; margin: 20px 0;">
                        {pin}
                    </div>
                    <p style="font-size: 12px; color: #8b949e; margin-bottom: 0;">This PIN will expire in 5 minutes.</p>
                </div>
            </body>
        </html>
        """
        send_email_in_background(subject, body, admin_email)
        
    msg = "Temporary PIN sent to email." if smtp_configured else "Temporary PIN generated. Check server console logs."
    return {"status": "ok", "message": msg}


@app.post("/api/admin/verify-pin")
def verify_pin(req: VerifyPinRequest):
    if not auth_store.active_pin:
        raise HTTPException(status_code=401, detail="No PIN has been generated.")
    if time.time() > auth_store.pin_expires_at:
        raise HTTPException(status_code=401, detail="PIN has expired.")
    if req.pin != auth_store.active_pin:
        raise HTTPException(status_code=401, detail="Incorrect PIN.")
        
    auth_store.active_pin = None
    auth_store.pin_expires_at = 0.0
    
    token = secrets.token_hex(24)
    auth_store.sessions[token] = time.time() + 7200  # 2 hours
    
    return {"status": "ok", "token": token}


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
