"""
Market data layer (yfinance, free, no API key).

Fetches WEEKLY OHLCV for a ticker plus weekly SPX (^GSPC) for Mansfield RS.
"""

from __future__ import annotations

import time

import pandas as pd
import yfinance as yf
import streamlit as st


SPX_SYMBOL = "^GSPC"   # S&P 500 index - yfinance equivalent of TradingView "SPX"


def _history_with_retry(symbol: str, period: str, attempts: int = 3) -> pd.DataFrame:
    """yfinance history() with simple backoff (Yahoo throttles cloud IPs)."""
    last_err = None
    for i in range(attempts):
        try:
            df = yf.Ticker(symbol).history(period=period, interval="1wk", auto_adjust=False)
            if df is not None and not df.empty:
                return df
            last_err = ValueError(f"Empty response for '{symbol}'.")
        except Exception as e:  # noqa: BLE001 - surface after retries
            last_err = e
        time.sleep(1.5 * (i + 1))
    raise ValueError(f"No data returned for '{symbol}' after {attempts} attempts ({last_err}).")


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_weekly(ticker: str, period: str = "10y") -> pd.DataFrame:
    """Return weekly OHLCV indexed by date with lowercase columns."""
    df = _history_with_retry(ticker, period)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    df = df.dropna(subset=["open", "high", "low", "close"])
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_spx_weekly(period: str = "10y") -> pd.Series:
    """Return weekly SPX close as a Series indexed by date."""
    try:
        spx = _history_with_retry(SPX_SYMBOL, period)
    except ValueError:
        return pd.Series(dtype=float)
    s = spx["Close"].copy()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    s.name = "spx_close"
    return s


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_financial_info(ticker: str) -> dict:
    """Fetch key financial metrics and cash flow info for the ticker using yfinance."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        
        # Also try to get Free Cash Flow from cashflow statement
        fcf_history = []
        try:
            cashflow_df = t.cashflow
            if cashflow_df is not None and not cashflow_df.empty:
                # Find matching row for Free Cash Flow (case-insensitive check)
                fcf_row = None
                for idx in cashflow_df.index:
                    if str(idx).strip().lower() == "free cash flow":
                        fcf_row = cashflow_df.loc[idx]
                        break
                if fcf_row is not None:
                    fcf_series = fcf_row.dropna()
                    fcf_history = [{"date": str(date)[:10], "val": float(val)} for date, val in fcf_series.items()]
        except Exception:
            pass
            
        return {
            "info": info,
            "fcf_history": fcf_history
        }
    except Exception:
        return {"info": {}, "fcf_history": []}


@st.cache_data(show_spinner=False, ttl=86400)
def resolve_name(ticker: str) -> str:
    """Best-effort company/long name for display. Falls back to the ticker."""
    try:
        data = fetch_financial_info(ticker)
        info = data.get("info") or {}
        return info.get("longName") or info.get("shortName") or ticker.upper()
    except Exception:
        return ticker.upper()


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_news(ticker: str) -> list:
    """Fetch recent news articles for a ticker from yfinance."""
    try:
        t = yf.Ticker(ticker)
        return t.news or []
    except Exception:
        return []

