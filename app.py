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
import textwrap

import data as datalib
from indicator import HGSettings, compute


def render_html(html_str: str):
    """Clean all leading/trailing whitespace from each line of HTML to prevent Markdown parser from interpreting indented HTML as code blocks."""
    if not html_str:
        return
    cleaned_lines = [line.strip() for line in html_str.splitlines()]
    cleaned_html = "\n".join(cleaned_lines)
    st.markdown(cleaned_html, unsafe_allow_html=True)


st.set_page_config(page_title="Holygrail — Long Term Momentum Scanner", layout="wide",
                   initial_sidebar_state="expanded")

# --- Header & Settings ------------------------------------------------------
col_title, col_settings = st.columns([3, 1])

with col_title:
    st.markdown(
        "## 🏆 Holygrail\n"
        "An entertaining tool that captures long term momentum in public securities based on probabilities."
    )

with col_settings:
    st.write("")  # Vertical alignment spacer
    with st.popover("⚙️ Settings & Thresholds", use_container_width=True):
        show_cloud = st.checkbox("Show EMA cloud", True)
        
        with st.expander("EMA / MA", expanded=False):
            ema_fast = st.number_input("EMA Fast", 1, 200, 5)
            ema_mid = st.number_input("EMA Mid", 1, 200, 9)
            ema_slow = st.number_input("EMA Slow", 1, 200, 21)
            ma50w = st.number_input("50-Week MA", 1, 400, 50)
            
        with st.expander("Rules", expanded=False):
            rsi_len = st.number_input("RSI Length", 2, 100, 14)
            vol_mult = st.number_input("Breakout Vol Multiplier", 0.1, 10.0, 1.5, 0.1)
            vol_lookbk = st.number_input("Vol Avg Lookback (wks)", 1, 200, 10)
            retest_max = st.number_input("Max % Above 50WMA for Retest", 0.5, 100.0, 15.0, 0.5)
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
            
    st.markdown(
        "<div style='text-align: right; font-size: 0.72rem; font-style: italic; color: rgba(250, 250, 250, 0.45); margin-top: 4px;'>"
        "For best experience, switch to dark mode by clicking the 3-dot button"
        "</div>",
        unsafe_allow_html=True
    )

# --- Sidebar: search & navigation -------------------------------------------
default_ticker = "ARM"
if "ticker" in st.query_params:
    val = st.query_params["ticker"]
    if val:
        default_ticker = str(val).strip().upper()

with st.sidebar:
    col_nav, col_bell = st.columns([4, 1])
    with col_nav:
        st.markdown("### 🧭 Navigation")
    with col_bell:
        st.components.v1.html(
            """
            <div class="bell-container">
              <button id="bell-btn" class="bell-btn" onclick="toggleNotifications()" title="Toggle Alerts">
                <svg viewBox="0 0 24 24" id="bell-svg" class="bell-svg">
                  <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
                </svg>
              </button>
            </div>

            <style>
              body {
                margin: 0;
                padding: 0;
                background: transparent;
                overflow: hidden;
                display: flex;
                justify-content: flex-end;
                align-items: center;
                height: 100vh;
              }
              .bell-container {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 32px;
                width: 32px;
              }
              .bell-btn {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 50%;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s ease;
                padding: 0;
                outline: none;
              }
              .bell-btn:hover {
                background: rgba(255, 255, 255, 0.08);
                border-color: rgba(255, 255, 255, 0.2);
              }
              .bell-svg {
                width: 16px;
                height: 16px;
                fill: rgba(250, 250, 250, 0.45);
                transition: fill 0.2s ease;
              }
              .bell-btn:hover .bell-svg {
                fill: rgba(250, 250, 250, 0.8);
              }
              .bell-btn.active {
                background: rgba(0, 230, 118, 0.1);
                border-color: rgba(0, 230, 118, 0.3);
              }
              .bell-btn.active .bell-svg {
                fill: #00e676;
              }
            </style>

            <script>
              let notifyEnabled = localStorage.getItem("hg_alerts_enabled") === "true";
              const bellBtn = document.getElementById("bell-btn");

              function updateVisuals() {
                if (notifyEnabled) {
                  bellBtn.classList.add("active");
                } else {
                  bellBtn.classList.remove("active");
                }
              }

              updateVisuals();

              function playAlertSound() {
                try {
                  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                  const osc = audioCtx.createOscillator();
                  const gain = audioCtx.createGain();
                  osc.connect(gain);
                  gain.connect(audioCtx.destination);
                  osc.frequency.setValueAtTime(659.25, audioCtx.currentTime);
                  gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
                  gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
                  osc.start(audioCtx.currentTime);
                  osc.stop(audioCtx.currentTime + 0.3);
                  setTimeout(() => {
                    const osc2 = audioCtx.createOscillator();
                    const gain2 = audioCtx.createGain();
                    osc2.connect(gain2);
                    gain2.connect(audioCtx.destination);
                    osc2.frequency.setValueAtTime(880.00, audioCtx.currentTime);
                    gain2.gain.setValueAtTime(0.15, audioCtx.currentTime);
                    gain2.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
                    osc2.start(audioCtx.currentTime);
                    osc2.stop(audioCtx.currentTime + 0.4);
                  }, 120);
                } catch (e) {
                  console.log("Audio play blocked", e);
                }
              }

              function toggleNotifications() {
                if (notifyEnabled) {
                  notifyEnabled = false;
                  localStorage.setItem("hg_alerts_enabled", "false");
                } else {
                  notifyEnabled = true;
                  localStorage.setItem("hg_alerts_enabled", "true");
                  playAlertSound();
                  
                  if ("Notification" in window) {
                    Notification.requestPermission();
                  }
                }
                updateVisuals();
                window.dispatchEvent(new Event('storage'));
              }

              window.addEventListener('storage', () => {
                const val = localStorage.getItem("hg_alerts_enabled") === "true";
                if (val !== notifyEnabled) {
                  notifyEnabled = val;
                  updateVisuals();
                }
              });
            </script>
            """,
            height=40,
            scrolling=False
        )

    if "nav_selection" not in st.session_state:
        st.session_state["nav_selection"] = "🔍 Scanner"
    nav_page = st.radio(
        "Navigation",
        ["🔍 Scanner", "📖 Guide", "🌟 Expert Corner"],
        key="nav_selection",
        label_visibility="collapsed"
    )

    if nav_page == "🔍 Scanner":
        st.header("🔎 Ticker")
        with st.form(key="scanner_form", clear_on_submit=False, border=False):
            ticker_input = st.text_input("Symbol", value=default_ticker, help="e.g. AAPL, MSFT, NVDA, TSLA, SPY").strip().upper()
            go_btn = st.form_submit_button("Scan", type="primary", use_container_width=True)
            
        if go_btn and ticker_input:
            if st.query_params.get("ticker") != ticker_input:
                st.query_params["ticker"] = ticker_input
                st.rerun()
                
        ticker = ticker_input
        history_choice = st.select_slider("History", options=["3 Months", "6 Months", "YTD", "1 Year", "2 Years", "5 Years"], value="1 Year")

        st.write("---")
        st.markdown("### 📖 How to read the chart")
        st.markdown(
            "* <span style='color: #1d4ed8; font-size: 1.1rem;'>▲</span> **Weekly Dark Blue Triangle (HG)**: Indicates a **Full Holy Grail Setup** and the best time to enter a stock.\n"
            "* 🟡 **Yellow Dot**: Indicates a **Partial Setup** representing a medium confidence level to enter a stock.\n"
            "* <span style='color: #e040fb; font-size: 1.1rem;'>■</span> **HRR (High Risk Reward)**: Indicates Red to Green EMA cloud flip (crossover), representing a **high risk high reward** entry week.",
            unsafe_allow_html=True
        )
    else:
        history_choice = "1 Year"
        ticker = default_ticker

    # --- Alerts / Notifications Worker ---
    st.components.v1.html(
        """
        <div id="alert-box" class="alert-box hidden">
          <div class="alert-header">
            <span class="alert-icon">⚡</span>
            <span class="alert-title">Expert Corner Update</span>
            <button class="dismiss-btn" onclick="dismissAlert()">×</button>
          </div>
          <div id="alert-body" class="alert-body"></div>
        </div>

        <style>
          body {
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: rgba(250, 250, 250, 0.95);
            overflow: hidden;
          }
          .alert-box {
            background: linear-gradient(135deg, rgba(224, 64, 251, 0.18) 0%, rgba(22, 199, 132, 0.08) 100%);
            border: 1px solid rgba(224, 64, 251, 0.4);
            border-radius: 8px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease forwards;
            margin-top: 10px;
          }
          .hidden {
            display: none !important;
          }
          .alert-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.75rem;
            color: rgba(250, 250, 250, 0.6);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          .alert-title {
            flex-grow: 1;
            margin-left: 6px;
          }
          .dismiss-btn {
            background: none;
            border: none;
            color: rgba(250, 250, 250, 0.5);
            font-size: 1.2rem;
            cursor: pointer;
            line-height: 1;
            padding: 0;
          }
          .dismiss-btn:hover {
            color: rgba(250, 250, 250, 0.9);
          }
          .alert-body {
            font-size: 0.85rem;
            line-height: 1.4;
          }
          @keyframes slideIn {
            from {
              opacity: 0;
              transform: translateY(5px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        </style>

        <script>
          const alertBox = document.getElementById("alert-box");
          const alertBody = document.getElementById("alert-body");

          function playAlertSound() {
            try {
              const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
              const osc = audioCtx.createOscillator();
              const gain = audioCtx.createGain();
              osc.connect(gain);
              gain.connect(audioCtx.destination);
              osc.frequency.setValueAtTime(659.25, audioCtx.currentTime);
              gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
              gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
              osc.start(audioCtx.currentTime);
              osc.stop(audioCtx.currentTime + 0.3);
              setTimeout(() => {
                const osc2 = audioCtx.createOscillator();
                const gain2 = audioCtx.createGain();
                osc2.connect(gain2);
                gain2.connect(audioCtx.destination);
                osc2.frequency.setValueAtTime(880.00, audioCtx.currentTime);
                gain2.gain.setValueAtTime(0.15, audioCtx.currentTime);
                gain2.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
                osc2.start(audioCtx.currentTime);
                osc2.stop(audioCtx.currentTime + 0.4);
              }, 120);
            } catch (e) {
              console.log("Audio play blocked", e);
            }
          }

          function triggerAlert(ticker, verdict, price) {
            playAlertSound();
            
            if ("Notification" in window && Notification.permission === "granted") {
              try {
                new Notification("Expert Corner Updated!", {
                  body: `${ticker} updated to ${verdict} at $${price.toFixed(2)}`,
                  icon: "https://cdn-icons-png.flaticon.com/512/3602/3602145.png"
                });
              } catch (e) {
                console.log("Native notification failed", e);
              }
            }
            
            alertBody.innerHTML = `Ticker <strong>${ticker}</strong> updated to <strong>${verdict}</strong> at <strong>$${price.toFixed(2)}</strong>.`;
            alertBox.classList.remove("hidden");
          }

          function dismissAlert() {
            alertBox.classList.add("hidden");
          }

          const watchlistUrl = "https://raw.githubusercontent.com/ravichandran-urmila/holygrail-app/master/watchlist.json";

          function checkWatchlist() {
            const notifyEnabled = localStorage.getItem("hg_alerts_enabled") === "true";
            if (!notifyEnabled) return;
            
            fetch(watchlistUrl + "?nocache=" + new Date().getTime())
              .then(response => response.json())
              .then(data => {
                if (!Array.isArray(data)) return;
                
                const lastDataStr = localStorage.getItem("hg_watchlist_last");
                if (!lastDataStr) {
                  localStorage.setItem("hg_watchlist_last", JSON.stringify(data));
                  return;
                }
                
                const lastData = JSON.parse(lastDataStr);
                localStorage.setItem("hg_watchlist_last", JSON.stringify(data));
                
                data.forEach(item => {
                  const matchingLast = lastData.find(x => x.ticker === item.ticker);
                  if (!matchingLast) {
                    triggerAlert(item.ticker, item.verdict, item.price_added);
                  } else if (matchingLast.price_added !== item.price_added || matchingLast.verdict !== item.verdict) {
                    triggerAlert(item.ticker, item.verdict, item.price_added);
                  }
                });
              })
              .catch(err => console.error("Alert check error:", err));
          }

          checkWatchlist();
          setInterval(checkWatchlist, 30000);
        </script>
        """,
        height=120,
        scrolling=False
    )


settings = HGSettings(
    ema_fast=ema_fast, ema_mid=ema_mid, ema_slow=ema_slow, ma50w=ma50w,
    rsi_len=rsi_len, vol_mult=vol_mult, vol_lookbk=vol_lookbk,
    retest_max=retest_max, base_min=base_min,
    w1=w1, w2=w2, w3=w3, w4=w4, w5=w5, w6=w6,
    partial_thresh=partial_thresh, full_thresh=full_thresh,
)


def render_guide():
    st.markdown("### 📖 How to Read the Charts")
    st.markdown(
        "This educational section explains the core indicators and momentum rules of the Holy Grail system, "
        "using three real-world case studies to demonstrate high-probability entries and value traps."
    )
    st.write("---")
    
    # 1. Indicator Definitions
    st.markdown("#### 🛠️ Core Indicators & Momentum Rules")
    col_ind1, col_ind2 = st.columns(2)
    with col_ind1:
        st.markdown(
            """
            * <span style="display: inline-block; width: 20px; height: 3px; background-color: #ffd600; vertical-align: middle; margin-right: 8px; border-radius: 1px;"></span> 50-Week Moving Average (50WMA): The spine of the system. It separates long-term bullish regimes from bearish regimes. 
              - Rule: If the candles are below the 50WMA, there is no setup. Period.
            * <span style="color: #1d4ed8; font-size: 1.5rem; vertical-align: middle; margin-right: 6px;">▲</span> Holy Grail (HG) Setup (Dark Blue Triangle): The apex setup. It represents the ultimate confluence of momentum rules (price in the 50WMA retest zone, green EMA cloud, positive Mansfield RS, and RSI > 50). This signal has the highest probability of capturing a structural trend change.
            """,
            unsafe_allow_html=True
        )
    with col_ind2:
        st.markdown(
            """
            * 🟪 HRR (High Risk Reward) (Purple Square): Triggered when the fast EMA5 crosses above the slow EMA21 (red to green cloud flip). This is an early entry signal with high potential payoff, but it is inherently risky because the overall trend is not yet fully confirmed.
            * 🟡 Partial Setup (Yellow Dot): Indicates the stock is in a retest zone with a high score, but is missing 1 or 2 core criteria. The stock is 'almost perfect', but staying patient and waiting for full confirmation is the best state.
            """
        )
    
    st.write("---")

    # Helper to fetch guide data safely
    def fetch_guide_data(ticker_symbol: str):
        try:
            ohlcv = datalib.fetch_weekly(ticker_symbol, period="10y")
            spx = datalib.fetch_spx_weekly(period="10y")
            res_guide = compute(ohlcv, spx_close=spx if not spx.empty else None, settings=settings)
            return res_guide.df
        except Exception as e_guide:
            st.error(f"Error loading {ticker_symbol} historical data: {e_guide}")
            return None

    # 2. ARM Example
    st.markdown("#### 1. ARM Holdings (ARM) — The Apex Setup (March – April 2026)")
    col_text, col_chart = st.columns([2, 3])
    with col_text:
        st.markdown(
            """
            <p>What Happened:<br>
            ARM formed a prolonged consolidation and base above the 50WMA throughout late 2025 and early 2026.</p>
            <p>The Setup (HG Rules):</p>
            <ul>
              <li>&#128293; Full HG Setup Triggered: On March 30, 2026 and April 6, 2026, ARM triggered a Full Holy Grail Setup at a close price of $149 (with the rising 50WMA at $135.67).</li>
              <li>&#128293; Confluence of Rules:
                <ul>
                  <li>The price sat directly in the retest zone of the rising 50WMA.</li>
                  <li>The EMA cloud flipped green (EMA5/9/21 compression crossover).</li>
                  <li>The Mansfield RS was highly positive.</li>
                  <li>RSI was above 50.</li>
                </ul>
              </li>
              <li>&#128293; The Result: This perfect confluence of indicators triggered a legendary momentum launch, with ARM surging from $149 to $353 by late May 2026 — a +135% gain in under 2 months!</li>
            </ul>
            """,
            unsafe_allow_html=True
        )
    with col_chart:
        df_arm = fetch_guide_data("ARM")
        if df_arm is not None:
            df_arm_filtered = df_arm.loc['2025-08-01':'2026-06-01']
            fig_arm = build_chart(df_arm_filtered, "ARM", show_cloud=True)
            fig_arm.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_arm, use_container_width=True, key="guide_arm_chart")
            
    st.write("---")
    
    # 3. AMD Example
    st.markdown("#### 2. AMD (AMD) — Winning Trades Repeated (June 2025 – Present)")
    col_text, col_chart = st.columns([2, 3])
    with col_text:
        st.markdown(
            """
            <p>What Happened:<br>
            AMD consolidated and established a solid support base above its rising 50WMA during early 2025.</p>
            <p>The Setup (HG Rules):</p>
            <ul>
              <li>&#9989; HG Setup Triggered: On June 23, 2025, AMD triggered a Full Holy Grail Setup (score of 0.75) at a close price of $143.81 (resting on a 50WMA of $126.60).</li>
              <li>&#9989; Mansfield RS Green: The Mansfield Relative Strength turned positive (0.4469), confirming that AMD's relative momentum vs. the S&amp;P 500 had shifted in its favor.</li>
              <li>&#9989; The Result: By entering the trade in this low-risk retest zone, investors captured repeated winning trades as the stock went on to surge +273% to $537.37 by June 2026.</li>
            </ul>
            """,
            unsafe_allow_html=True
        )
    with col_chart:
        df_amd = fetch_guide_data("AMD")
        if df_amd is not None:
            df_amd_filtered = df_amd.loc['2025-01-01':'2026-06-19']
            fig_amd = build_chart(df_amd_filtered, "AMD", show_cloud=True)
            fig_amd.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_amd, use_container_width=True, key="guide_amd_chart")
            
    st.write("---")
    
    # 4. Adobe Example
    st.markdown("#### 3. Adobe (ADBE) — The Risks & The Traps (December 2024 – June 2025)")
    col_text, col_chart = st.columns([2, 3])
    with col_text:
        st.markdown(
            """
            <p>What Happened:<br>
            Adobe illustrates the dual lessons of HRR risk and the absolute rule of the 50WMA.</p>
            <p>The Setups &amp; Traps:</p>
            <ul>
              <li>&#128683; HRR Failure (December 2, 2024): A HRR signal (Purple Square) triggered at $552.96 as the EMA cloud flipped green. However, because the underlying relative strength was weak (Mansfield RS was red at -0.91), the setup failed immediately, dropping -15.8% to $465.69 the very next week.</li>
              <li>&#128683; The Value Trap (April - June 2025): Adobe fell into the low $330s and staged a rapid rally back to $417. Value hunters piled in believing it was cheap. However, the price remained strictly below the declining 50WMA, and Mansfield RS remained negative.</li>
              <li>&#128683; The Result: Because candles below the 50WMA mean there is no setup, the momentum never shifted and the stock collapsed back to the $340s in July, trapping buyers.</li>
            </ul>
            """,
            unsafe_allow_html=True
        )
    with col_chart:
        df_adbe = fetch_guide_data("ADBE")
        if df_adbe is not None:
            df_adbe_filtered = df_adbe.loc['2024-10-01':'2025-08-01']
            fig_adbe = build_chart(df_adbe_filtered, "ADBE", show_cloud=True)
            fig_adbe.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_adbe, use_container_width=True, key="guide_adbe_chart")


def render_expert_corner():
    st.markdown("### 🌟 Expert Corner")
    st.markdown("This list is curated by the admin and displays specific tickers, entry prices, and current returns.")

    import base64
    import json
    import os
    import datetime
    import requests as _requests

    WATCHLIST_FILE = "watchlist.json"
    _GH_API = "https://api.github.com"

    def _gh_cfg():
        """Return (token, repo, branch, path) or None if not configured."""
        try:
            token  = st.secrets.get("GITHUB_TOKEN", "")
            repo   = st.secrets.get("GITHUB_REPO", "")
            branch = st.secrets.get("GITHUB_BRANCH", "master")
            path   = st.secrets.get("GITHUB_FILE_PATH", "watchlist.json")
            if token and repo:
                return token, repo, branch, path
        except Exception:
            pass
        return None

    def load_wl():
        """Load watchlist — GitHub first, local file as fallback."""
        cfg = _gh_cfg()
        if cfg:
            token, repo, branch, path = cfg
            try:
                headers = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                r = _requests.get(
                    f"{_GH_API}/repos/{repo}/contents/{path}?ref={branch}",
                    headers=headers, timeout=10,
                )
                if r.status_code == 200:
                    raw = base64.b64decode(r.json()["content"]).decode("utf-8")
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        return data.get("items", [])
                    return data
            except Exception:
                pass  # fall through to local file

        # Local fallback (dev mode)
        if os.path.exists(WATCHLIST_FILE):
            try:
                with open(WATCHLIST_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data.get("items", [])
                    return data
            except Exception:
                pass
        return []

    def save_wl(data):
        """Save watchlist — commits directly to GitHub so it survives re-deploys."""
        payload_str = json.dumps(data, indent=2)
        cfg = _gh_cfg()

        if cfg:
            token, repo, branch, path = cfg
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            try:
                # Need the file's current SHA to update it
                r_get = _requests.get(
                    f"{_GH_API}/repos/{repo}/contents/{path}?ref={branch}",
                    headers=headers, timeout=10,
                )
                sha = r_get.json().get("sha", "") if r_get.status_code == 200 else ""

                body = {
                    "message": "chore: update watchlist via admin panel",
                    "content": base64.b64encode(payload_str.encode()).decode(),
                    "branch": branch,
                }
                if sha:
                    body["sha"] = sha

                r_put = _requests.put(
                    f"{_GH_API}/repos/{repo}/contents/{path}",
                    headers=headers, json=body, timeout=15,
                )
                if r_put.status_code in (200, 201):
                    return True
                st.error(f"GitHub save failed ({r_put.status_code}): {r_put.json().get('message', r_put.text)}")
                return False
            except Exception as e:
                st.error(f"GitHub save error: {e}")
                return False

        # Local fallback (dev mode)
        try:
            with open(WATCHLIST_FILE, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Failed to save watchlist locally: {e}")
            return False

    watchlist = sorted(load_wl(), key=lambda x: x.get("date_added", ""), reverse=True)

    if not watchlist:
        st.info("Expert Corner is currently empty. Add tickers in the Admin Panel below.")
    else:
        wl_rows = []
        with st.spinner("Fetching current prices for watchlist..."):
            for item in watchlist:
                t = item["ticker"]
                d_add = item["date_added"]
                p_add = item["price_added"]
                v_word = item.get("verdict", "WATCH")
                comm = item.get("commentary", "")
                
                try:
                    # Fetch the latest price from yfinance (cached via fetch_weekly)
                    p_curr = float(datalib.fetch_weekly(t, period="1mo")["close"].iloc[-1])
                    gain = ((p_curr - p_add) / p_add) * 100.0
                except Exception:
                    p_curr = None
                    gain = None
                
                wl_rows.append({
                    "ticker": t,
                    "date_added": d_add,
                    "price_added": p_add,
                    "current_price": p_curr,
                    "verdict": v_word,
                    "commentary": comm,
                    "gain": gain,
                })

        VERDICT_COLOR = {"BUY": "#00e676", "WATCH": "#ffd600", "HOLD": "#38b6ff", "AVOID": "#ea3943"}

        rows_html = ""
        for row in wl_rows:
            v_color = VERDICT_COLOR.get(row["verdict"], "#888888")
            tooltip = row["commentary"].replace("'", "&#39;").replace('"', "&quot;")
            
            if row["gain"] is None:
                gain_html = "<span style='color: rgba(250,250,250,0.4);'>N/A</span>"
            else:
                gain_val = row["gain"]
                sign = "+" if gain_val >= 0 else ""
                gain_color = "#16c784" if gain_val >= 0 else "#ea3943"
                gain_html = f"<span style='color: {gain_color}; font-weight: bold;'>{sign}{gain_val:.2f}%</span>"

            curr_price_str = f"${row['current_price']:.2f}" if row["current_price"] is not None else "<span style='color: rgba(250,250,250,0.4);'>N/A</span>"
            
            rows_html += (
                f"<tr>"
                f"<td style='padding: 12px; color: rgba(250,250,250,0.75);'>{row['date_added']}</td>"
                f"<td style='padding: 12px; font-weight: 700;'><a href='?ticker={row['ticker']}' target='_self'>{row['ticker']}</a></td>"
                f"<td style='padding: 12px; color: rgba(250,250,250,0.85);'>${row['price_added']:.2f}</td>"
                f"<td style='padding: 12px; color: rgba(250,250,250,0.85);'>{curr_price_str}</td>"
                f"<td style='padding: 12px;'>"
                f"<span title='{tooltip}' style='color:{v_color}; font-weight:700; "
                f"padding:4px 10px; border-radius:4px; background:rgba(255,255,255,0.05); "
                f"border:1px solid {v_color}40; text-decoration:underline dotted; cursor:help;'>"
                f"{row['verdict']}</span>"
                f"</td>"
                f"<td style='padding: 12px;'>{gain_html}</td>"
                f"</tr>"
            )

        table_html = f"""
        <style>
        .expert-table-container {{
            overflow-x: auto;
            width: 100%;
            -webkit-overflow-scrolling: touch;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            background: rgba(255,255,255,0.01);
            margin-bottom: 20px;
        }}
        .expert-table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 600px;
            font-family: inherit;
        }}
        .expert-table th {{
            padding: 12px;
            color: rgba(250,250,250,0.5);
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            border-bottom: 2px solid rgba(255,255,255,0.12);
            text-align: left;
            background: rgba(0,0,0,0.2);
        }}
        .expert-table td {{
            padding: 12px;
            font-size: 0.92rem;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            vertical-align: middle;
        }}
        .expert-table tr:last-child td {{
            border-bottom: none;
        }}
        .expert-table tr:hover td {{
            background: rgba(255,255,255,0.02);
        }}
        .expert-table a {{
            color: #38b6ff;
            text-decoration: none;
            font-weight: 700;
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            background: rgba(56, 182, 255, 0.08);
            border: 1px solid rgba(56, 182, 255, 0.15);
            transition: all 0.2s ease;
        }}
        .expert-table a:hover {{
            color: #00e676;
            background: rgba(0, 230, 118, 0.08);
            border-color: rgba(0, 230, 118, 0.2);
            text-decoration: none;
            box-shadow: 0 0 8px rgba(0, 230, 118, 0.1);
        }}
        </style>
        <div class="expert-table-container">
            <table class="expert-table">
                <thead>
                    <tr>
                        <th>Date Added</th>
                        <th>Ticker</th>
                        <th>Price Added</th>
                        <th>Current Price</th>
                        <th>Verdict</th>
                        <th>Gain / Loss</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """
        st.markdown(table_html, unsafe_allow_html=True)

    st.write("---")
    
    # Admin controls section
    with st.expander("🛠️ Admin Expert Corner Controls", expanded=False):
        admin_pass = st.text_input("Admin Password", type="password", key="wl_admin_pass")
        try:
            correct_pass = st.secrets.get("admin_password", "holygrail")
        except Exception:
            correct_pass = "holygrail"
        
        if admin_pass == correct_pass:
            st.success("Authorized!")
            col_add, col_del = st.columns(2)
            
            with col_add:
                st.markdown("#### ➕ Add Ticker to Expert Corner")
                add_ticker = st.text_input("Ticker Symbol", value="NVDA", key="wl_add_tick").strip().upper()
                add_date = st.date_input("Date Added", value=datetime.date.today(), key="wl_add_date")
                
                add_verdict = st.selectbox("Ticker Verdict", ["BUY", "WATCH", "HOLD", "AVOID"], index=1, key="wl_add_verd")
                add_comm = st.text_area("Ticker Commentary (Hover Tooltip)", value="", placeholder="Enter detailed commentary that users will see on hover...", key="wl_add_comm")
                
                if "fetched_price" not in st.session_state:
                    st.session_state["fetched_price"] = 0.0
                
                if st.button("🔍 Auto-fetch Close Price for Date", use_container_width=True):
                    if add_ticker:
                        with st.spinner(f"Fetching close price for {add_ticker} around {add_date}..."):
                            try:
                                import yfinance as yf
                                start_t = datetime.datetime.combine(add_date, datetime.time.min)
                                end_t = start_t + datetime.timedelta(days=7)
                                hist = yf.Ticker(add_ticker).history(start=start_t.strftime('%Y-%m-%d'), end=end_t.strftime('%Y-%m-%d'))
                                if not hist.empty:
                                    fetched = float(hist["Close"].iloc[0])
                                    st.session_state["fetched_price"] = fetched
                                    st.toast(f"Successfully fetched price: ${fetched:.2f}", icon="✅")
                                else:
                                    st.error("No trading data found for this date. Market might have been closed.")
                            except Exception as e:
                                st.error(f"Error fetching price: {e}")
                
                add_price = st.number_input("Price Added", value=st.session_state["fetched_price"], format="%.2f", key="wl_add_price")
                
                if st.button("Save to Expert Corner", type="primary", use_container_width=True):
                    if not add_ticker:
                        st.error("Please enter a ticker symbol.")
                    elif add_price <= 0:
                        st.error("Please enter a valid price (> 0).")
                    else:
                        new_item = {
                            "ticker": add_ticker,
                            "date_added": add_date.strftime("%Y-%m-%d"),
                            "price_added": float(add_price),
                            "verdict": add_verdict,
                            "commentary": add_comm
                        }
                        watchlist = [x for x in watchlist if x["ticker"] != add_ticker]
                        watchlist.append(new_item)
                        if save_wl(watchlist):
                            st.toast(f"Saved {add_ticker} to Expert Corner!", icon="🚀")
                            st.rerun()
            
            with col_del:
                st.markdown("#### ❌ Remove from Expert Corner")
                if not watchlist:
                    st.info("Expert Corner is empty.")
                else:
                    tickers_to_remove = st.multiselect("Select Ticker(s) to Remove", options=[x["ticker"] for x in watchlist])
                    if st.button("Remove Selected", type="secondary", use_container_width=True):
                        if tickers_to_remove:
                            watchlist = [x for x in watchlist if x["ticker"] not in tickers_to_remove]
                            if save_wl(watchlist):
                                st.toast(f"Removed {', '.join(tickers_to_remove)} from Expert Corner!", icon="🗑️")
                                st.rerun()
                        else:
                            st.warning("Please select at least one ticker to remove.")
            
            st.write("---")
            if _gh_cfg():
                st.success(
                    "✅ **GitHub persistence is active.** All changes are committed directly "
                    "to your repository and will survive every re-deployment."
                )
            else:
                st.warning(
                    "⚠️ **GitHub persistence is NOT configured.** Changes save to the local "
                    "file only and will be lost on the next deployment.\n\n"
                    "Add these four keys to your Streamlit Cloud **Secrets** to enable "
                    "permanent persistence:\n"
                    "```toml\n"
                    'GITHUB_TOKEN     = "ghp_your_token_here"\n'
                    'GITHUB_REPO      = "ravichandran-urmila/holygrail-app"\n'
                    'GITHUB_BRANCH    = "master"\n'
                    'GITHUB_FILE_PATH = "watchlist.json"\n'
                    "```\n"
                    "Generate a token at **GitHub → Settings → Developer settings → "
                    "Fine-grained personal access tokens** with *Contents: Read & write* "
                    "permission on this repository."
                )
        elif admin_pass:
            st.error("Incorrect password.")


def render(ticker: str):
    if not ticker:
        st.info("Enter a ticker in the sidebar and press **Scan**.")
        return

    try:
        with st.spinner(f"Fetching weekly data for {ticker}…"):
            ohlcv = datalib.fetch_weekly(ticker, period="10y")
            spx = datalib.fetch_spx_weekly(period="10y")
            name = datalib.resolve_name(ticker)
            news_items = datalib.fetch_news(ticker)
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
    elif history_choice == "6 Months":
        start_date = now - datetime.timedelta(days=180)
    elif history_choice == "YTD":
        start_date = datetime.datetime(now.year, 1, 1)
    elif history_choice == "1 Year":
        start_date = now - datetime.timedelta(days=365)
    elif history_choice == "2 Years":
        start_date = now - datetime.timedelta(days=2 * 365)
    else: # "5 Years"
        start_date = now - datetime.timedelta(days=5 * 365)

    df_filtered = df[df.index >= start_date]

    # ---- Top verdict banner ------------------------------------------------
    # ---- Verdict parsing ---------------------------------------------------
    verdict = sm["verdict"]
    verdict_emoji = {"COMPLETE SETUP": "🚀", "WATCHING": "👀", "NO SETUP": "—"}[verdict]
    verdict_color = {"COMPLETE SETUP": "#00e676", "WATCHING": "#ffd600", "NO SETUP": "#888888"}[verdict]

    # ---- Top verdict banner ------------------------------------------------
    st.markdown(
        f"<h3>{name} &middot; {ticker} &nbsp;&nbsp;&nbsp;&nbsp; "
        f"<span style='font-size: 1.05rem; padding: 5px 12px; border-radius: 6px; "
        f"background-color: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.1); "
        f"color: {verdict_color}; vertical-align: middle; font-weight: 600;'>{verdict_emoji} {verdict}</span></h3>",
        unsafe_allow_html=True
    )
    st.write("") # Spacing

    c1, c2, c3, c4 = st.columns([1.0, 1.0, 1.3, 1.7])
    c1.metric("Last weekly close", f"${sm['last_close']:.2f}")
    c2.metric("Weighted score", f"{sm['weighted_score']:.2f} / {sm['total_weight']:.2f}")
    with c3:
        if sm["last_hg_date"] is not None:
            gain_pct = sm["last_hg_gain_pct"]
            gain_color = "#16c784" if gain_pct >= 0 else "#ea3943"
            gain_sign = "+" if gain_pct >= 0 else ""
            render_html(f"""
                <div style="font-family: inherit; line-height: 1.2; padding-top: 2px;">
                    <div style="font-size: 0.875rem; color: rgba(250, 250, 250, 0.6); margin-bottom: 4px;">Gain from HG Signal</div>
                    <div style="font-size: 1.8rem; font-weight: 600; color: {gain_color}; margin-bottom: 4px;">
                        {gain_sign}{gain_pct:.2f}%
                    </div>
                    <div style="font-size: 0.85rem; color: rgba(250, 250, 250, 0.6); font-weight: 500;">
                        at ${sm['last_hg_entry']:.2f} ({sm['last_hg_date'].strftime('%Y-%m-%d')})
                    </div>
                </div>
            """)
        else:
            render_html(f"""
                <div style="font-family: inherit; line-height: 1.2; padding-top: 2px;">
                    <div style="font-size: 0.875rem; color: rgba(250, 250, 250, 0.6); margin-bottom: 4px;">Gain from HG Signal</div>
                    <div style="font-size: 1.8rem; font-weight: 600; color: rgba(250, 250, 250, 0.4); margin-bottom: 4px;">
                        N/A
                    </div>
                    <div style="font-size: 0.85rem; color: rgba(250, 250, 250, 0.4); font-weight: 500;">
                        No signals in history
                    </div>
                </div>
            """)
    with c4:
        render_html(f"""
            <div style="font-family: inherit; line-height: 1.2; padding-top: 2px;">
                <div style="font-size: 0.875rem; color: rgba(250, 250, 250, 0.6); margin-bottom: 4px;">Entry Range</div>
                <div style="font-size: 1.8rem; font-weight: 600; color: rgb(250, 250, 250); margin-bottom: 4px;">
                    ${sm['entry_price_low']:.2f} – ${sm['entry_price_high']:.2f}
                </div>
                <div style="font-size: 0.85rem; color: #ea3943; font-weight: 500;">
                    🛑 stop: ${sm['stop_price']:.2f}
                </div>
            </div>
        """)

    if sm["full_setup"]:
        st.success("🚀 **FULL Holy Grail Setup** on the latest weekly bar.")
    elif sm["partial_setup"]:
        st.warning("⚠️ **Entering the 50WMA retest zone** with an elevated weighted score.")

    chart_tab, dash_tab, data_tab = st.tabs(["📈 Chart", "📋 Dashboard", "🔢 Data"])

    with chart_tab:
        fig = build_chart(df_filtered, ticker, show_cloud)
        st.plotly_chart(fig, use_container_width=True)

        with st.spinner("Analyzing catalysts and pattern data..."):
            ai_summary_html, tech_source = generate_ai_summary(ticker, name, res, settings)
            fundamental_html, fundamental_source = generate_fundamental_summary(ticker, name)
            narrative_html, narrative_source = generate_catalyst_narrative(ticker, name, news_items)

        col_left, col_mid, col_right = st.columns(3)
        with col_left:
            render_html(f"""
            <div style="
                background: linear-gradient(135deg, rgba(224, 64, 251, 0.08) 0%, rgba(22, 199, 132, 0.02) 100%);
                border: 1px solid rgba(224, 64, 251, 0.2);
                border-radius: 12px;
                padding: 20px;
                margin-top: 15px;
                margin-bottom: 20px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                min-height: 330px;
            ">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center;">
                        <span style="font-size: 1.3rem; margin-right: 8px;">🧠</span>
                        <span style="font-weight: 600; font-size: 1.1rem; color: #e040fb; letter-spacing: 0.5px; text-transform: uppercase;">AI Technical Analyst</span>
                    </div>
                    <span style="font-size: 0.72rem; padding: 2px 7px; border-radius: 4px; background-color: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.5);">{tech_source}</span>
                </div>
                <div style="font-family: inherit; font-size: 0.95rem; line-height: 1.6; color: rgba(250, 250, 250, 0.95);">
                    {ai_summary_html}
                </div>
            </div>
            """)

        with col_mid:
            render_html(f"""
            <div style="
                background: linear-gradient(135deg, rgba(0, 188, 212, 0.08) 0%, rgba(22, 199, 132, 0.02) 100%);
                border: 1px solid rgba(0, 188, 212, 0.2);
                border-radius: 12px;
                padding: 20px;
                margin-top: 15px;
                margin-bottom: 20px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                min-height: 330px;
            ">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center;">
                        <span style="font-size: 1.3rem; margin-right: 8px;">📊</span>
                        <span style="font-weight: 600; font-size: 1.1rem; color: #00bcd4; letter-spacing: 0.5px; text-transform: uppercase;">AI Fundamental Analyst</span>
                    </div>
                    <span style="font-size: 0.72rem; padding: 2px 7px; border-radius: 4px; background-color: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.5);">{fundamental_source}</span>
                </div>
                <div style="font-family: inherit; font-size: 0.95rem; line-height: 1.6; color: rgba(250, 250, 250, 0.95);">
                    {fundamental_html}
                </div>
            </div>
            """)

        with col_right:
            render_html(f"""
            <div style="
                background: linear-gradient(135deg, rgba(255, 145, 0, 0.08) 0%, rgba(22, 199, 132, 0.02) 100%);
                border: 1px solid rgba(255, 145, 0, 0.2);
                border-radius: 12px;
                padding: 20px;
                margin-top: 15px;
                margin-bottom: 20px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                min-height: 330px;
            ">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center;">
                        <span style="font-size: 1.3rem; margin-right: 8px;">📰</span>
                        <span style="font-weight: 600; font-size: 1.1rem; color: #ff9100; letter-spacing: 0.5px; text-transform: uppercase;">Current Narrative</span>
                    </div>
                    <span style="font-size: 0.72rem; padding: 2px 7px; border-radius: 4px; background-color: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.5);">{narrative_source}</span>
                </div>
                <div style="font-family: inherit; font-size: 0.95rem; line-height: 1.6; color: rgba(250, 250, 250, 0.95);">
                    {narrative_html}
                </div>
            </div>
            """)


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
            f"Suggested entry range: ${sm['entry_price_low']:.2f} - ${sm['entry_price_high']:.2f} (50WMA to +{settings.retest_max:.1f}%) · "
            f"stop ${sm['stop_price']:.2f} (50WMA ×0.995, on weekly close)."
        )

    # ---- Raw data ----------------------------------------------------------
    with data_tab:
        cols = ["open", "high", "low", "close", "volume", "ma50w", "ema5", "ema9",
                "ema21", "rsi14", "pct_above_50w", "mansfield_rs", "weighted_score",
                "full_setup", "partial_setup", "blue_square"]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df_filtered[cols].iloc[::-1], use_container_width=True)
        st.download_button(
            "Download full series (CSV)",
            df[cols].to_csv().encode(),
            file_name=f"{ticker}_holygrail.csv",
            mime="text/csv",
        )

def clean_html_response(text: str) -> str:
    if not text:
        return ""
    import re
    text = text.strip()
    code_block_match = re.search(r"```(?:html)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if code_block_match:
        text = code_block_match.group(1).strip()
    else:
        html_tag_match = re.search(r"(<[a-zA-Z]+.*?>.*)", text, re.DOTALL)
        if html_tag_match:
            text = html_tag_match.group(1).strip()
    text = text.replace("```", "")
    return text.strip()


def generate_ai_summary(ticker: str, name: str, res, settings) -> tuple[str, str]:
    import json
    import requests
    import re
    import numpy as np

    df = res.df
    sm = res.summary
    last_row = df.iloc[-1]

    # Gather technical snapshot
    last_close = sm["last_close"]
    weighted_score = sm["weighted_score"]
    total_weight = sm["total_weight"]
    verdict = sm["verdict"]

    # Gather status of each rule
    rule_status = []
    for rname, rstat, rval, _passed in res.dashboard:
        rule_status.append(f"- {rname}: {rstat} ({rval})")
    rules_text = "\n".join(rule_status)

    entry_low = sm["entry_price_low"]
    entry_high = sm["entry_price_high"]
    stop_price = sm["stop_price"]

    # Calculate weeks since last Holy Grail setup (full_setup == True) and get HG week close
    hg_weeks_ago = None
    hg_close_price = None
    if sm.get("last_hg_date") is not None:
        idx_list = list(df.index)
        try:
            pos = idx_list.index(sm["last_hg_date"])
            hg_weeks_ago = len(idx_list) - 1 - pos
            hg_close_price = float(df.loc[sm["last_hg_date"], "close"])
        except ValueError:
            pass

    above_50wma = last_close >= last_row["ma50w"] if ("ma50w" in last_row and not np.isnan(last_row["ma50w"])) else False

    # Determine if API keys are available in st.secrets
    gemini_key = None
    openai_key = None
    hf_token = None
    try:
        if "GEMINI_API_KEY" in st.secrets:
            gemini_key = st.secrets["GEMINI_API_KEY"]
        if "OPENAI_API_KEY" in st.secrets:
            openai_key = st.secrets["OPENAI_API_KEY"]
        if "HF_TOKEN" in st.secrets:
            hf_token = st.secrets["HF_TOKEN"]
        elif "HUGGINGFACE_API_KEY" in st.secrets:
            hf_token = st.secrets["HUGGINGFACE_API_KEY"]
    except Exception:
        pass

    # Construct history description for prompt
    hg_history_prompt = ""
    if hg_weeks_ago is not None and hg_close_price is not None:
        pct_from_hg_close = ((last_close - hg_close_price) / hg_close_price) * 100.0
        hg_history_prompt = f"A COMPLETE Holy Grail setup was triggered {hg_weeks_ago} week(s) ago (on the week close of ${hg_close_price:.2f}). "
        
        is_in_range = (pct_from_hg_close <= 15.0) and above_50wma
        if is_in_range:
            hg_history_prompt += f"The current close (${last_close:.2f}) is {pct_from_hg_close:.1f}% from the setup close, which is within the 15% trading range and remains above the 50WMA (${last_row['ma50w']:.2f}). This indicates it is still a good time to buy (prime buying zone)."
        elif above_50wma:
            hg_history_prompt += f"The current close (${last_close:.2f}) is {pct_from_hg_close:.1f}% above the setup close, which exceeds the 15% trading range (extended), meaning it is too high/extended to buy right now."
        else:
            hg_history_prompt += f"However, the price has since dropped below the 50WMA, invalidating the buy setup."
    else:
        hg_history_prompt = "No COMPLETE Holy Grail setup has been triggered in the history."

    prompt = f"""You are a professional stock market technical analyst. Write a highly concise, structured, and non-wordy executive summary analyzing the stock {name} ({ticker}) based on the Holy Grail setup rules.

Holy Grail Setup Status:
- {hg_history_prompt}
- Current Setup Verdict: {verdict}
- Latest Close: ${last_close:.2f}
- Weighted Score: {weighted_score:.2f} / {total_weight:.2f}

Rules breakdown:
{rules_text}

Entry/Exit Strategy:
- Suggested Entry Range: ${entry_low:.2f} to ${entry_high:.2f} (50WMA to +{settings.retest_max:.1f}%)
- Suggested Stop Loss: ${stop_price:.2f} (50WMA * 0.995 on a weekly closing basis)

CRITICAL INSTRUCTIONS:
1. Restructure the analysis to be concise and not wordy (use short, bulleted points or tight sentences).
2. Acknowledge the most recent Holy Grail setup. Explain that it is currently a good time to buy if the price is still above the 50WMA and is within 15% of the Holy Grail week's closing price. If the current close is more than 15% above the Holy Grail closing price, highlight that the stock is extended (not a good time to buy).
3. Format in raw HTML using <p>, <strong>, <ul>, <li>. Do not wrap in markdown or code blocks. Keep under 120 words."""

    # Try Gemini API if key is available
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 300,
                    "temperature": 0.4
                }
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    text = clean_html_response(text)
                    return text, "Gemini 2.5 Flash API"
        except Exception:
            pass

    # Try OpenAI API if key is available
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.4
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()
                if text:
                    text = clean_html_response(text)
                    return text, "GPT-4o-mini API"
        except Exception:
            pass

    # Try Hugging Face Inference API if token is available
    if hf_token:
        hf_models = [
            "Qwen/Qwen2.5-7B-Instruct",
            "google/gemma-2-2b-it",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "microsoft/Phi-3-mini-4k-instruct",
            "HuggingFaceH4/zephyr-7b-beta"
        ]
        for model in hf_models:
            # 1. Try Chat Completion API (handles templates automatically)
            try:
                chat_url = f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {hf_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 250,
                    "temperature": 0.4
                }
                resp = requests.post(chat_url, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    if text:
                        text = clean_html_response(text)
                        return text, f"Hugging Face ({model.split('/')[-1]})"
            except Exception:
                pass

            # 2. Try raw endpoint if Chat API is not supported / failed
            try:
                std_url = f"https://api-inference.huggingface.co/models/{model}"
                headers = {
                    "Authorization": f"Bearer {hf_token}",
                    "Content-Type": "application/json"
                }
                formatted_input = f"<s>[INST] {prompt} [/INST]" if "mistral" in model.lower() or "zephyr" in model.lower() else prompt
                payload = {
                    "inputs": formatted_input,
                    "parameters": {
                        "max_new_tokens": 250,
                        "temperature": 0.4,
                        "return_full_text": False
                    }
                }
                resp = requests.post(std_url, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        text = data[0].get("generated_text", "").strip()
                        if text:
                            text = clean_html_response(text)
                            return text, f"Hugging Face ({model.split('/')[-1]})"
            except Exception:
                pass

    # Programmatic Rules-Based Generator Fallback
    # Bullet 1: Setup History & Buy Signal
    if hg_weeks_ago is not None and hg_close_price is not None:
        pct_from_hg_close = ((last_close - hg_close_price) / hg_close_price) * 100.0
        
        if above_50wma and pct_from_hg_close <= 15.0:
            history_html = f"<li>🟢 <strong>Holy Grail Buy Zone</strong>: A complete buy setup occurred <strong>{hg_weeks_ago} week(s) ago</strong> (HG week close: ${hg_close_price:.2f}). The current price is within the 15% range (<strong>{pct_from_hg_close:.1f}%</strong> above close) and remains above the 50WMA, placing it in a <strong>prime buying zone</strong>.</li>"
        elif above_50wma:
            history_html = f"<li>⚠️ <strong>Extended Price</strong>: A complete buy setup occurred <strong>{hg_weeks_ago} week(s) ago</strong> (HG week close: ${hg_close_price:.2f}). The current price is <strong>{pct_from_hg_close:.1f}%</strong> above the setup close, which is outside the 15% trading range (extended).</li>"
        else:
            history_html = f"<li>❌ <strong>Setup Invalidated</strong>: A complete buy setup occurred <strong>{hg_weeks_ago} week(s) ago</strong> (HG week close: ${hg_close_price:.2f}), but the price has since dropped below the 50WMA.</li>"
    else:
        history_html = "<li>⚠️ <strong>No Active Setup</strong>: No complete Holy Grail setup was triggered in history.</li>"

    # Verdict Title
    if verdict == "COMPLETE SETUP":
        status_title = "🚀 Complete Buy Setup"
    elif verdict == "WATCHING":
        status_title = "👀 On Close Watch"
    else:
        status_title = "⚠️ No Active Setup"

    verdict_html = f"<p><strong>{status_title}</strong> ({weighted_score:.2f}/{total_weight:.2f}):</p>"

    # Technical Details
    retest_val = last_row["pct_above_50w"]
    if np.isnan(retest_val):
        retest_desc = "Insufficient history for 50WMA."
    else:
        retest_desc = f"Price is <strong>{retest_val:.1f}%</strong> above the 50WMA (${last_row['ma50w']:.2f})." if retest_val >= 0 else f"Price is <strong>{-retest_val:.1f}%</strong> below the 50WMA (${last_row['ma50w']:.2f})."

    vol_desc = "Strong volume breakout confirmed." if bool(last_row["rule2_breakout"]) else "No recent volume breakout."
    rs_desc = "Relative strength is bullish (Mansfield RS > 0)." if (("mansfield_rs" in last_row and not np.isnan(last_row["mansfield_rs"])) and bool(last_row["rule5_mansfield"])) else "Underperforming the S&P 500."
    
    technical_bullets = f"""
    <ul>
        {history_html}
        <li>📊 <strong>Trend</strong>: {retest_desc} {vol_desc} {rs_desc}</li>
        <li>🎯 <strong>Strategy</strong>: Buy between <strong>${entry_low:.2f} and ${entry_high:.2f}</strong>. Stop-loss at <strong>${stop_price:.2f}</strong> on a weekly close.</li>
    </ul>
    """

    fallback_html = f"{verdict_html}{technical_bullets}"
    return fallback_html, "Local Expert System"


def generate_fundamental_summary(ticker: str, name: str) -> tuple[str, str]:
    import requests
    import json
    import re
    import numpy as np

    # Fetch cached fundamental data
    data = datalib.fetch_financial_info(ticker)
    info = data.get("info") or {}
    fcf_history = data.get("fcf_history") or []

    # Extract metrics
    ev_ebitda = info.get("enterpriseToEbitda")
    trailing_pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    ps = info.get("priceToSalesTrailing12Months")
    peg = info.get("pegRatio")
    fcf = info.get("freeCashflow")
    mcap = info.get("marketCap")

    # Format descriptions
    ev_ebitda_desc = f"{ev_ebitda:.2f}" if ev_ebitda is not None else "N/A"
    trailing_pe_desc = f"{trailing_pe:.2f}" if trailing_pe is not None else "N/A"
    forward_pe_desc = f"{forward_pe:.2f}" if forward_pe is not None else "N/A"
    ps_desc = f"{ps:.2f}" if ps is not None else "N/A"
    peg_desc = f"{peg:.2f}" if peg is not None else "N/A"

    # 4. P/FCF
    p_fcf = None
    p_fcf_desc = "N/A"
    if mcap and fcf:
        p_fcf = mcap / fcf
        p_fcf_desc = f"{p_fcf:.2f}"
    elif fcf and fcf < 0:
        p_fcf_desc = "Negative FCF"

    # 5. YoY FCF Growth
    fcf_growth_pct = None
    fcf_growth_desc = "N/A"
    if len(fcf_history) >= 2:
        val0 = fcf_history[0].get("val")
        val1 = fcf_history[1].get("val")
        if val0 is not None and val1 is not None and val1 != 0:
            fcf_growth_pct = ((val0 - val1) / abs(val1)) * 100.0
            fcf_growth_desc = f"{fcf_growth_pct:+.1f}%"

    # 6. P/FCF to Growth Ratio
    p_fcf_growth_desc = "N/A"
    if p_fcf is not None and fcf_growth_pct is not None and fcf_growth_pct > 0:
        p_fcf_growth = p_fcf / fcf_growth_pct
        p_fcf_growth_desc = f"{p_fcf_growth:.2f}"

    # Determine if API keys are available in st.secrets
    gemini_key = None
    openai_key = None
    hf_token = None
    try:
        if "GEMINI_API_KEY" in st.secrets:
            gemini_key = st.secrets["GEMINI_API_KEY"]
        if "OPENAI_API_KEY" in st.secrets:
            openai_key = st.secrets["OPENAI_API_KEY"]
        if "HF_TOKEN" in st.secrets:
            hf_token = st.secrets["HF_TOKEN"]
        elif "HUGGINGFACE_API_KEY" in st.secrets:
            hf_token = st.secrets["HUGGINGFACE_API_KEY"]
    except Exception:
        pass

    prompt = f"""You are a professional fundamental stock market analyst. Write a highly concise, structured, and non-wordy executive summary analyzing the fundamental health of the stock {name} ({ticker}).

Key Financial Metrics:
- Trailing PE: {trailing_pe_desc}
- Forward PE: {forward_pe_desc}
- PS Ratio: {ps_desc}
- PEG Ratio: {peg_desc}
- EV/EBITDA: {ev_ebitda_desc}
- Price to Free Cash Flow (P/FCF): {p_fcf_desc}
- YoY Free Cash Flow Growth: {fcf_growth_desc}
- Price to FCF Growth Ratio (P/FCF / Growth): {p_fcf_growth_desc}

CRITICAL INSTRUCTIONS:
1. Explain what these valuation and cash flow metrics mean for the stock (undervalued, fairly valued, or overvalued/extended).
2. Keep the analysis concise, structured (using bullet points or bold keys), and under 120 words.
3. Format in raw HTML using <p>, <strong>, <ul>, <li>. Do not wrap in markdown or code blocks. Keep the style modern and professional."""

    # Try Gemini API if key is available
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 300,
                    "temperature": 0.4
                }
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    text = clean_html_response(text)
                    return text, "Gemini (Fundamental)"
        except Exception:
            pass

    # Try OpenAI API if key is available
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 250,
                "temperature": 0.4
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()
                if text:
                    text = clean_html_response(text)
                    return text, "OpenAI (Fundamental)"
        except Exception:
            pass

    # Try Hugging Face API if token is available
    if hf_token:
        models = [
            "Qwen/Qwen2.5-7B-Instruct",
            "google/gemma-2-2b-it",
            "microsoft/Phi-3-mini-4k-instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "HuggingFaceH4/zephyr-7b-beta"
        ]
        for model in models:
            # Try chat API first
            try:
                chat_url = f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {hf_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 250,
                    "temperature": 0.4
                }
                resp = requests.post(chat_url, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    if text:
                        text = clean_html_response(text)
                        return text, f"HF ({model.split('/')[-1]})"
            except Exception:
                pass

            # Try raw endpoint
            try:
                std_url = f"https://api-inference.huggingface.co/models/{model}"
                headers = {
                    "Authorization": f"Bearer {hf_token}",
                    "Content-Type": "application/json"
                }
                formatted_input = f"<s>[INST] {prompt} [/INST]" if "mistral" in model.lower() or "zephyr" in model.lower() else prompt
                payload = {
                    "inputs": formatted_input,
                    "parameters": {
                        "max_new_tokens": 250,
                        "temperature": 0.4,
                        "return_full_text": False
                    }
                }
                resp = requests.post(std_url, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        text = data[0].get("generated_text", "").strip()
                        if text:
                            text = clean_html_response(text)
                            return text, f"HF ({model.split('/')[-1]})"
            except Exception:
                pass

    # Programmatic Rules-Based Generator Fallback
    mcap_desc = f"${mcap/1e9:.1f}B" if mcap else "N/A"
    
    valuation_signals = []
    if ev_ebitda is not None:
        if ev_ebitda < 12.0:
            valuation_signals.append("EV/EBITDA is undervalued")
        elif ev_ebitda > 25.0:
            valuation_signals.append("EV/EBITDA is premium-priced")
    if forward_pe is not None:
        if forward_pe < 15.0:
            valuation_signals.append("Forward PE suggests value pricing")
        elif forward_pe > 35.0:
            valuation_signals.append("Forward PE is growth-priced")
            
    val_verdict_str = ", ".join(valuation_signals) if valuation_signals else "Valuation ratios are within standard industry bounds."
    
    growth_verdict = "YoY Free Cash Flow growth is negative or unavailable, suggesting some near-term operational friction."
    if fcf_growth_pct is not None:
        if fcf_growth_pct > 20.0:
            growth_verdict = f"YoY Free Cash Flow growth is very strong at <strong>{fcf_growth_desc}</strong>, indicating a powerful, expanding business model."
        elif fcf_growth_pct > 0:
            growth_verdict = f"YoY Free Cash Flow growth is healthy at <strong>{fcf_growth_desc}</strong>, reflecting steady business scale."

    fallback_html = f"""
    <p><strong>Valuation Snapshot</strong> (Market Cap: {mcap_desc}):</p>
    <ul>
        <li>📊 <strong>Valuation</strong>: PE: <strong>{trailing_pe_desc}</strong> (Trailing) / <strong>{forward_pe_desc}</strong> (Forward) | PS: <strong>{ps_desc}</strong> | PEG: <strong>{peg_desc}</strong> | EV/EBITDA: <strong>{ev_ebitda_desc}</strong>.</li>
        <li>💡 <strong>Context</strong>: {val_verdict_str}</li>
        <li>💰 <strong>Cash Flow</strong>: P/FCF: <strong>{p_fcf_desc}</strong> | Growth: <strong>{fcf_growth_desc}</strong>. {growth_verdict}</li>
    </ul>
    """
    return fallback_html, "Local Expert System"


def generate_catalyst_narrative(ticker: str, name: str, news_items: list) -> tuple[str, str]:
    import requests
    import json
    import re
    import time
    from datetime import datetime, timezone, timedelta

    # Filter out empty/invalid items and items older than 14 days (2 weeks)
    valid_news = []
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=14)

    if news_items:
        for item in news_items:
            # yfinance now nests everything inside a "content" sub-dict
            content = item.get("content", item)  # fallback to item itself for legacy format

            title = content.get("title")
            if not title:
                continue

            # Publisher: nested provider dict OR flat "publisher" key
            provider = content.get("provider") or {}
            publisher = provider.get("displayName") if isinstance(provider, dict) else None
            publisher = publisher or content.get("publisher") or "Unknown"

            # Link: canonicalUrl dict OR clickThroughUrl dict OR flat "link" key
            canon = content.get("canonicalUrl") or {}
            click = content.get("clickThroughUrl") or {}
            link = (canon.get("url") if isinstance(canon, dict) else None) \
                or (click.get("url") if isinstance(click, dict) else None) \
                or content.get("link") or "#"

            # Date filter: pubDate (ISO string) OR providerPublishTime (unix ts)
            pub_date_str = content.get("pubDate")
            pub_ts = content.get("providerPublishTime")

            if pub_date_str:
                try:
                    pub_dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                    if pub_dt < cutoff_dt:
                        continue
                except Exception:
                    pass
            elif pub_ts:
                try:
                    if float(pub_ts) < cutoff_dt.timestamp():
                        continue
                except Exception:
                    pass

            valid_news.append({
                "title": title,
                "publisher": publisher,
                "link": link,
            })

    # Limit to top 5 news items for prompt
    news_subset = valid_news[:5]

    # Format news items for the LLM
    news_text = ""
    for idx, item in enumerate(news_subset):
        news_text += f"{idx+1}. \"{item['title']}\" (published by {item['publisher']})\n"

    # If no news is available, we return a fallback message
    if not news_subset:
        msg = f"<p>No recent news catalysts were found for <strong>{name} ({ticker})</strong> in Yahoo Finance. The stock's narrative is currently driven by standard macroeconomic updates and historical sector trends.</p>"
        return msg, "Local System"

    # Determine if API keys are available in st.secrets
    gemini_key = None
    openai_key = None
    hf_token = None
    try:
        if "GEMINI_API_KEY" in st.secrets:
            gemini_key = st.secrets["GEMINI_API_KEY"]
        if "OPENAI_API_KEY" in st.secrets:
            openai_key = st.secrets["OPENAI_API_KEY"]
        if "HF_TOKEN" in st.secrets:
            hf_token = st.secrets["HF_TOKEN"]
        elif "HUGGINGFACE_API_KEY" in st.secrets:
            hf_token = st.secrets["HUGGINGFACE_API_KEY"]
    except Exception:
        pass

    prompt = f"""You are a professional financial journalist and stock market catalyst analyst. 
Analyze the following recent news headlines for {name} ({ticker}) and synthesize them into a concise, unified "current narrative" summary (max 120 words). 
Identify what key catalyst (e.g., earnings, product launch, regulatory news, macroeconomic trends, analyst upgrades) is potentially moving the stock.

Recent News Headlines for {ticker}:
{news_text}

CRITICAL FORMATTING INSTRUCTIONS:
Format your response in raw HTML (using tags like <p>, <strong>, <br/>). Do not include <html> or <body> tags, do not wrap in code blocks (like ```html), and keep the response under 120 words."""

    # Try Gemini API if key is available
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 300,
                    "temperature": 0.4
                }
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    text = clean_html_response(text)
                    return text, "Gemini 2.5 Flash API"
        except Exception:
            pass

    # Try OpenAI API if key is available
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.4
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()
                if text:
                    text = clean_html_response(text)
                    return text, "GPT-4o-mini API"
        except Exception:
            pass

    # Try Hugging Face Inference API if token is available
    if hf_token:
        hf_models = [
            "Qwen/Qwen2.5-7B-Instruct",
            "google/gemma-2-2b-it",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "microsoft/Phi-3-mini-4k-instruct",
            "HuggingFaceH4/zephyr-7b-beta"
        ]
        for model in hf_models:
            # 1. Try Chat Completion API (handles templates automatically)
            try:
                chat_url = f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {hf_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 250,
                    "temperature": 0.4
                }
                resp = requests.post(chat_url, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    if text:
                        text = clean_html_response(text)
                        return text, f"Hugging Face ({model.split('/')[-1]})"
            except Exception:
                pass

            # 2. Try raw endpoint if Chat API is not supported / failed
            try:
                std_url = f"https://api-inference.huggingface.co/models/{model}"
                headers = {
                    "Authorization": f"Bearer {hf_token}",
                    "Content-Type": "application/json"
                }
                formatted_input = f"<s>[INST] {prompt} [/INST]" if "mistral" in model.lower() or "zephyr" in model.lower() else prompt
                payload = {
                    "inputs": formatted_input,
                    "parameters": {
                        "max_new_tokens": 250,
                        "temperature": 0.4,
                        "return_full_text": False
                    }
                }
                resp = requests.post(std_url, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        text = data[0].get("generated_text", "").strip()
                        if text:
                            text = clean_html_response(text)
                            return text, f"Hugging Face ({model.split('/')[-1]})"
            except Exception:
                pass

    # Programmatic Fallback: List of top 3 news items with direct links
    fallback_html = f"<p>Recent news headlines indicating potential catalysts for <strong>{name} ({ticker})</strong>:</p>"
    fallback_html += "<ul style='margin-left: 15px; padding-left: 0;'>"
    for item in valid_news[:3]:
        fallback_html += f"<li style='margin-bottom: 8px;'><a href='{item['link']}' target='_blank' style='color: #ff9100; text-decoration: underline;'>{item['title']}</a> <span style='color: rgba(255, 255, 255, 0.5); font-size: 0.85rem;'>({item['publisher']})</span></li>"
    fallback_html += "</ul>"

    return fallback_html, "Recent Yahoo News"


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

    # Highlight the weeks with full setup in a soft green shade
    full = df[df["full_setup"]]
    if not full.empty:
        for date in full.index:
            x0 = date - pd.Timedelta(days=3.5)
            x1 = date + pd.Timedelta(days=3.5)
            fig.add_vrect(
                x0=x0, x1=x1,
                fillcolor="#16c784", opacity=0.12,
                layer="below", line_width=0
            )

    # Full setup markers
    if not full.empty:
        fig.add_trace(go.Scatter(
            x=full.index, y=full["low"] * 0.97, mode="markers+text",
            marker=dict(symbol="triangle-up", size=16, color="#1d4ed8"),
            text=["HG"] * len(full), textposition="bottom center",
            textfont=dict(color="#1d4ed8", size=11), name="Full Setup",
            hoverinfo="skip",
        ))

    # Partial setup dots
    part = df[df["partial_setup"]]
    if not part.empty:
        fig.add_trace(go.Scatter(
            x=part.index, y=part["low"] * 0.98, mode="markers",
            marker=dict(symbol="circle", size=8, color="#ffd600"),
            name="Partial (watching)",
            hoverinfo="skip",
        ))

    # HRR (High Risk Reward) markers (red to green cloud crossover)
    if "blue_square" in df.columns:
        blue_sq = df[df["blue_square"]]
        if not blue_sq.empty:
            fig.add_trace(go.Scatter(
                x=blue_sq.index, y=blue_sq["low"] * 0.96, mode="markers",
                marker=dict(symbol="square", size=10, color="#e040fb"),
                name="HRR (High Risk Reward)",
                hoverinfo="skip",
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
if nav_page == "🔍 Scanner":
    render(ticker)
elif nav_page == "📖 Guide":
    render_guide()
elif nav_page == "🌟 Expert Corner":
    render_expert_corner()


