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
    history_choice = st.selectbox("History", ["3 Months", "YTD", "6 Months", "1 Year", "5 Years"], index=3)

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
            ohlcv = datalib.fetch_weekly(ticker, period="10y")
            spx = datalib.fetch_spx_weekly(period="10y")
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

    # Filter data for display (chart and data table)
    import datetime
    now = datetime.datetime.now()
    if history_choice == "3 Months":
        start_date = now - datetime.timedelta(days=90)
    elif history_choice == "YTD":
        start_date = datetime.datetime(now.year, 1, 1)
    elif history_choice == "6 Months":
        start_date = now - datetime.timedelta(days=180)
    elif history_choice == "1 Year":
        start_date = now - datetime.timedelta(days=365)
    else: # "5 Years"
        start_date = now - datetime.timedelta(days=5 * 365)

    df_filtered = df[df.index >= start_date]

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
        fig = build_chart(df_filtered, ticker, show_cloud)
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
        st.dataframe(df_filtered[cols].iloc[::-1], use_container_width=True)
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
        # EMA cloud fill — flips GREEN (ema5>ema21) / RED (ema5<ema21) per segment,
        # matching the Pine `fill(... ema5>ema21 ? green : red)` behavior.
        _add_ema_cloud(fig, df)
        # EMA lines drawn on top of the cloud
        fig.add_trace(go.Scatter(x=df.index, y=df["ema21"], line=dict(color="rgba(41,98,255,0.7)", width=1),
                                 name="EMA 21"))
        fig.add_trace(go.Scatter(x=df.index, y=df["ema9"], line=dict(color="rgba(0,170,170,0.7)", width=1),
                                 name="EMA 9"))
        fig.add_trace(go.Scatter(x=df.index, y=df["ema5"], line=dict(color="rgba(0,200,120,0.85)", width=1),
                                 name="EMA 5"))

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



    fig.update_layout(
        height=640, template="plotly_dark",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
    )
    return fig


def _add_ema_cloud(fig: go.Figure, df: pd.DataFrame):
    """Fill between EMA5 and EMA21, recoloring green/red wherever the cloud flips.

    Plotly's `fill="tonexty"` only takes one color per trace, so we split the
    series into contiguous runs of the same sign(ema5 - ema21) and draw each run
    as its own filled band. Runs are extended by one bar on the right so adjacent
    bands meet at the crossover with no visible gap.
    """
    ema5 = df["ema5"].to_numpy()
    ema21 = df["ema21"].to_numpy()
    idx = df.index
    n = len(df)
    if n == 0:
        return

    green = ema5 >= ema21          # True -> green band, False -> red band

    # Build contiguous runs of constant color.
    runs = []
    start = 0
    for i in range(1, n):
        if green[i] != green[start]:
            runs.append((start, i - 1, bool(green[start])))
            start = i
    runs.append((start, n - 1, bool(green[start])))

    GREEN_FILL = "rgba(22,199,132,0.22)"
    RED_FILL = "rgba(234,57,67,0.22)"
    legend_seen = set()

    for a, b, is_green in runs:
        end = min(b + 1, n - 1)         # bridge to next run's first bar
        xs = idx[a:end + 1]
        lower = ema21[a:end + 1]
        upper = ema5[a:end + 1]
        color = GREEN_FILL if is_green else RED_FILL
        key = "up" if is_green else "down"

        # invisible lower bound, then upper bound that fills down to it
        fig.add_trace(go.Scatter(x=xs, y=lower, mode="lines", line=dict(width=0),
                                 hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(
            x=xs, y=upper, mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor=color, hoverinfo="skip",
            name="EMA cloud ▲" if is_green else "EMA cloud ▼",
            legendgroup=key, showlegend=key not in legend_seen,
        ))
        legend_seen.add(key)





# --- Entry point ------------------------------------------------------------
# Render on load (default ticker) or whenever Scan is pressed.
render(ticker)


