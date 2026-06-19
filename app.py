"""
Holy Grail - Green Cloud Retest Scanner  (Streamlit app)
========================================================
Search a ticker -> pull the weekly candlestick chart -> overlay the
"Holy Grail" indicator (50WMA, EMA cloud, signal markers) and show the
exact dashboard the Pine Script renders on TradingView.

Run:  streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data as datalib
from indicator import HGSettings, compute


st.set_page_config(page_title="Holy Grail — Retest Scanner", layout="wide",
                   initial_sidebar_state="expanded")

# --- Header -----------------------------------------------------------------
st.markdown(
    "## 🏆 Holy Grail — Green Cloud Retest Scanner\n"
    "Weekly-timeframe scanner. Data: Yahoo Finance (free). "
    "Indicator logic ported 1:1 from the TradingView Pine v6 script."
)

# --- Sidebar: search + settings --------------------------------------------
with st.sidebar:
    st.header("🔎 Ticker")
    ticker = st.text_input("Symbol", value="AAPL", help="e.g. AAPL, MSFT, NVDA, TSLA, SPY").strip().upper()
    period = st.selectbox("History", ["5y", "10y", "max"], index=1)

    st.header("⚙️ Settings")
    with st.expander("EMA / MA", expanded=False):
        ema_fast = st.number_input("EMA Fast", 1, 200, 5)
        ema_mid = st.number_input("EMA Mid", 1, 200, 9)
        ema_slow = st.number_input("EMA Slow", 1, 200, 21)
        ma50w = st.number_input("50-Week MA", 1, 400, 50)
    with st.expander("Rules", expanded=False):
        rsi_len = st.number_input("RSI Length", 2, 100, 14)
        vol_mult = st.number_input("Breakout Vol Multiplier", 0.1, 10.0, 1.5, 0.1)
        vol_lookbk = st.number_input("Vol Avg Lookback (wks)", 1, 200, 10)
        retest_max = st.number_input("Max % Above 50WMA for Retest", 0.5, 100.0, 10.0, 0.5)
        base_min = st.number_input("Min Base Length (wks)", 1, 200, 15)
    with st.expander("Weights & Thresholds", expanded=False):
        w1 = st.number_input("W1 Retest", 0.0, 1.0, 0.15, 0.05)
        w2 = st.number_input("W2 Breakout", 0.0, 1.0, 0.10, 0.05)
        w3 = st.number_input("W3 Base Length", 0.0, 1.0, 0.10, 0.05)
        w4 = st.number_input("W4 Green Cloud", 0.0, 1.0, 0.25, 0.05)
        w5 = st.number_input("W5 Mansfield RS", 0.0, 1.0, 0.30, 0.05)
        w6 = st.number_input("W6 RSI > 50", 0.0, 1.0, 0.10, 0.05)
        partial_thresh = st.number_input("Partial threshold", 0.0, 2.0, 0.35, 0.05)
        full_thresh = st.number_input("Full threshold", 0.0, 2.0, 0.70, 0.05)

    show_cloud = st.checkbox("Show EMA cloud", True)
    go_btn = st.button("Scan", type="primary", use_container_width=True)


settings = HGSettings(
    ema_fast=ema_fast, ema_mid=ema_mid, ema_slow=ema_slow, ma50w=ma50w,
    rsi_len=rsi_len, vol_mult=vol_mult, vol_lookbk=vol_lookbk,
    retest_max=retest_max, base_min=base_min,
    w1=w1, w2=w2, w3=w3, w4=w4, w5=w5, w6=w6,
    partial_thresh=partial_thresh, full_thresh=full_thresh,
)


def render(ticker: str):
    if not ticker:
        st.info("Enter a ticker in the sidebar and press **Scan**.")
        return

    try:
        with st.spinner(f"Fetching weekly data for {ticker}…"):
            ohlcv = datalib.fetch_weekly(ticker, period=period)
            spx = datalib.fetch_spx_weekly(period=period)
            name = datalib.resolve_name(ticker)
    except Exception as e:
        st.error(f"Could not load **{ticker}** — {e}")
        return

    if len(ohlcv) < settings.ma50w + 2:
        st.warning(
            f"Only {len(ohlcv)} weekly bars available — need ≥ {settings.ma50w + 2} "
            "for the 50-week MA. Results may be incomplete."
        )

    res = compute(ohlcv, spx_close=spx if not spx.empty else None, settings=settings)
    df = res.df
    sm = res.summary

    # ---- Top verdict banner ------------------------------------------------
    st.subheader(f"{name}  ·  {ticker}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last weekly close", f"${sm['last_close']:.2f}")
    c2.metric("Weighted score", f"{sm['weighted_score']:.2f} / {sm['total_weight']:.2f}")
    verdict = sm["verdict"]
    verdict_emoji = {"COMPLETE SETUP": "🚀", "WATCHING": "👀", "NO SETUP": "—"}[verdict]
    c3.metric("Verdict", f"{verdict_emoji} {verdict}")
    c4.metric("Entry / Stop", f"${sm['entry_price']:.2f}", f"stop ${sm['stop_price']:.2f}")

    if sm["full_setup"]:
        st.success("🚀 **FULL Holy Grail Setup** on the latest weekly bar.")
    elif sm["partial_setup"]:
        st.warning("⚠️ **Entering the 50WMA retest zone** with an elevated weighted score.")

    chart_tab, dash_tab, data_tab = st.tabs(["📈 Chart", "📋 Dashboard", "🔢 Data"])

    # ---- Chart -------------------------------------------------------------
    with chart_tab:
        fig = build_chart(df, ticker, show_cloud)
        st.plotly_chart(fig, use_container_width=True)

    # ---- Dashboard (replicates the Pine table) -----------------------------
    with dash_tab:
        st.markdown("#### Rule dashboard (latest weekly bar)")
        rows = [{"Rule": rule, "Status": stat, "Value": value}
                for rule, stat, value, _passed in res.dashboard]
        dash_df = pd.DataFrame(rows)

        def _style(row):
            passed = "PASS" in row["Status"]
            c = "background-color: rgba(22,199,132,0.18)" if passed else "background-color: rgba(234,57,67,0.18)"
            return [c, c, ""]

        st.dataframe(
            dash_df.style.apply(_style, axis=1),
            use_container_width=True, hide_index=True,
        )

        st.markdown(
            f"**Weighted score:** {sm['weighted_score']:.2f} / {sm['total_weight']:.2f}  "
            f"→ **{verdict}**"
        )
        st.caption(
            f"Suggested entry ${sm['entry_price']:.2f} (50WMA ×1.005) · "
            f"stop ${sm['stop_price']:.2f} (50WMA ×0.995, on weekly close)."
        )

    # ---- Raw data ----------------------------------------------------------
    with data_tab:
        cols = ["open", "high", "low", "close", "volume", "ma50w", "ema5", "ema9",
                "ema21", "rsi14", "pct_above_50w", "mansfield_rs", "weighted_score",
                "full_setup", "partial_setup"]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df[cols].tail(60).iloc[::-1], use_container_width=True)
        st.download_button(
            "Download full series (CSV)",
            df[cols].to_csv().encode(),
            file_name=f"{ticker}_holygrail.csv",
            mime="text/csv",
        )


def build_chart(df: pd.DataFrame, ticker: str, show_cloud: bool) -> go.Figure:
    fig = go.Figure()

    # Candles
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name=ticker, increasing_line_color="#16c784", decreasing_line_color="#ea3943",
    ))

    if show_cloud:
        # EMA cloud fill (light green band between EMA5 and EMA21)
        fig.add_trace(go.Scatter(x=df.index, y=df["ema21"], line=dict(color="rgba(41,98,255,0.6)", width=1),
                                 name="EMA 21"))
        fig.add_trace(go.Scatter(x=df.index, y=df["ema5"], line=dict(color="rgba(0,200,120,0.7)", width=1),
                                 name="EMA 5", fill="tonexty",
                                 fillcolor="rgba(22,199,132,0.12)"))
        fig.add_trace(go.Scatter(x=df.index, y=df["ema9"], line=dict(color="rgba(0,170,170,0.6)", width=1),
                                 name="EMA 9"))

    # 50-week MA (the spine of the system)
    fig.add_trace(go.Scatter(x=df.index, y=df["ma50w"], line=dict(color="orange", width=3),
                             name="50-Week MA"))

    # Full setup markers
    full = df[df["full_setup"]]
    if not full.empty:
        fig.add_trace(go.Scatter(
            x=full.index, y=full["low"] * 0.97, mode="markers+text",
            marker=dict(symbol="triangle-up", size=16, color="#00e676"),
            text=["HG"] * len(full), textposition="bottom center",
            textfont=dict(color="#00e676", size=11), name="Full Setup",
        ))

    # Partial setup dots
    part = df[df["partial_setup"]]
    if not part.empty:
        fig.add_trace(go.Scatter(
            x=part.index, y=part["low"] * 0.98, mode="markers",
            marker=dict(symbol="circle", size=8, color="#ffd600"),
            name="Partial (watching)",
        ))

    # Retest-zone background shading
    _add_retest_bands(fig, df)

    fig.update_layout(
        height=640, template="plotly_dark",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
    )
    return fig


def _add_retest_bands(fig: go.Figure, df: pd.DataFrame):
    """Shade contiguous weeks where price sits in the retest zone."""
    in_zone = df["rule1_retest"].fillna(False).to_numpy()
    idx = df.index
    start = None
    for i, flag in enumerate(in_zone):
        if flag and start is None:
            start = idx[i]
        elif not flag and start is not None:
            fig.add_vrect(x0=start, x1=idx[i], fillcolor="rgba(22,199,132,0.08)",
                          line_width=0, layer="below")
            start = None
    if start is not None:
        fig.add_vrect(x0=start, x1=idx[-1], fillcolor="rgba(22,199,132,0.08)",
                      line_width=0, layer="below")


# --- Entry point ------------------------------------------------------------
# Render on load (default ticker) or whenever Scan is pressed.
render(ticker)

st.caption(
    "⚠️ Educational tool, not financial advice. TradingView has no public API for custom "
    "Pine indicators or raw data — this app re-implements the indicator and uses Yahoo Finance. "
    "Mansfield RS uses ^GSPC (S&P 500) as the benchmark."
)
