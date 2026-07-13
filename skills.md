# Holy Grail — Green Cloud Retest Scanner: Build Guide

> **Purpose**: This document is a complete blueprint for rebuilding the Holy Grail Streamlit app from scratch. It covers every file, every feature, every configuration detail, and every deployment step.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack & Dependencies](#2-technology-stack--dependencies)
3. [File Structure](#3-file-structure)
4. [File-by-File Build Instructions](#4-file-by-file-build-instructions)
   - [4.1 requirements.txt](#41-requirementstxt)
   - [4.2 data.py — Market Data Layer](#42-datapy--market-data-layer)
   - [4.3 indicator.py — Core Indicator Engine](#43-indicatorpy--core-indicator-engine)
   - [4.4 app.py — Streamlit UI Application](#44-apppy--streamlit-ui-application)
   - [4.5 watchlist.json — Persistent Watchlist Data](#45-watchlistjson--persistent-watchlist-data)
   - [4.6 Dockerfile](#46-dockerfile)
   - [4.7 run.sh](#47-runsh)
   - [4.8 .dockerignore](#48-dockerignore)
   - [4.9 .gitignore](#49-gitignore)
5. [The 6 Holy Grail Rules (Indicator Logic)](#5-the-6-holy-grail-rules-indicator-logic)
6. [Chart Markers & Visual Signals](#6-chart-markers--visual-signals)
7. [AI Technical Analyst Feature](#7-ai-technical-analyst-feature)
8. [Current Narrative (News Catalyst) Feature](#8-current-narrative-news-catalyst-feature)
9. [Expert Corner & Admin Panel](#9-expert-corner--admin-panel)
10. [Streamlit Cloud Secrets Configuration](#10-streamlit-cloud-secrets-configuration)
11. [Deployment Instructions](#11-deployment-instructions)
12. [Color Palette & Design Tokens](#12-color-palette--design-tokens)
13. [Known Pitfalls & Gotchas](#13-known-pitfalls--gotchas)

---

## 1. Project Overview

The Holy Grail app is a **weekly-timeframe stock scanner** that identifies high-probability entry points using a ported version of a TradingView Pine Script v6 indicator. It:

- Fetches weekly OHLCV data from Yahoo Finance (free, no API key needed)
- Computes 6 weighted rules (retest zone, breakout volume, base length, EMA cloud, Mansfield RS, RSI)
- Overlays candlestick charts with signal markers and an EMA cloud
- Provides AI-powered technical analysis and news catalyst summaries
- Includes an admin-curated expert corner with GitHub-backed persistence

**Live URL**: Deployed on Streamlit Community Cloud, auto-deploys from `master` branch of `ravichandran-urmila/holygrail-app`.

---

## 2. Technology Stack & Dependencies

| Component | Technology | Version |
|---|---|---|
| Framework | Streamlit | ≥ 1.30 |
| Market Data | yfinance | ≥ 0.2.40 |
| Charting | Plotly | ≥ 5.18 |
| Data Processing | pandas | ≥ 2.0 |
| Math | numpy | ≥ 1.24 |
| HTTP (AI + GitHub API) | requests | ≥ 2.31 |
| Python | CPython | 3.10+ (3.12 in Docker) |

**No AI SDK packages** are installed. Gemini and OpenAI are called via raw REST (`requests`).

---

## 3. File Structure

```
holygrail_app/
├── app.py              # Main Streamlit application (~1070 lines)
├── indicator.py        # Pine Script v6 port — core rule engine (~331 lines)
├── data.py             # yfinance data layer (~76 lines)
├── watchlist.json      # Admin-curated watchlist (persisted via GitHub API)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container support for Render / Fly.io / Railway
├── run.sh              # Startup script (reads $PORT env var)
├── .dockerignore       # Files excluded from Docker builds
├── .gitignore          # Files excluded from git
├── .python-version     # Python version hint file
└── README.md           # Project documentation
```

---

## 4. File-by-File Build Instructions

### 4.1 `requirements.txt`

```
streamlit>=1.30
yfinance>=0.2.40
plotly>=5.18
pandas>=2.0
numpy>=1.24
requests>=2.31
```

### 4.2 `data.py` — Market Data Layer

This file handles all external data fetching. It contains 4 cached functions:

| Function | Cache TTL | Purpose |
|---|---|---|
| `fetch_weekly(ticker, period="10y")` | 1 hour | Returns weekly OHLCV DataFrame with lowercase columns, timezone-naive index |
| `fetch_spx_weekly(period="10y")` | 1 hour | Returns weekly S&P 500 (`^GSPC`) close as a Series (for Mansfield RS) |
| `resolve_name(ticker)` | 24 hours | Returns the company's long name via `yf.Ticker(ticker).info` |
| `fetch_news(ticker)` | 30 minutes | Returns raw news list from `yf.Ticker(ticker).news` |

**Key implementation details:**
- `_history_with_retry(symbol, period, attempts=3)` wraps `yf.Ticker().history()` with exponential backoff (`1.5s * attempt`) because Yahoo Finance throttles cloud IPs
- Uses `interval="1wk"` and `auto_adjust=False` for weekly candles
- All index timestamps are localized to None (timezone-naive) for consistent comparison
- All functions use `@st.cache_data(show_spinner=False)` for performance

### 4.3 `indicator.py` — Core Indicator Engine

This is a faithful Python port of the Pine Script v6 indicator. It contains:

#### `HGSettings` dataclass
Default parameters mirroring Pine Script inputs:
```
ema_fast=5, ema_mid=9, ema_slow=21, ma50w=50, rsi_len=14
vol_mult=1.5, vol_lookbk=10, retest_max=15.0, base_min=15
Weights: w1=0.15, w2=0.10, w3=0.10, w4=0.25, w5=0.30, w6=0.10
Thresholds: partial=0.35, full=0.70
```

#### TA helper functions
- `ema(series, length)` — Pine `ta.ema` equivalent using `ewm(span=length, adjust=False)`
- `sma(series, length)` — Simple moving average with `rolling(window=length, min_periods=length)`
- `rsi(series, length)` — Wilder's RSI using RMA (`ewm(alpha=1/length, adjust=False)`)
- `crossover(a, b)` — `a` crosses above `b` this bar
- `crossunder(a, b)` — `a` crosses below `b` this bar

#### `compute(ohlcv, spx_close, settings)` → `HGResult`
The main function. Returns `HGResult(df, settings, dashboard, summary)`.

**Computed columns added to `df`:**
`ema5, ema9, ema21, ma50w, rsi14, vol_ratio, pct_above_50w, rule1–6, weighted_score, full_setup, partial_setup, stop_trigger, blue_square, weeks_since_breakout, captured_base_length, mansfield_rs, weeks_since_rs_green`

**Stateful loop (bar-by-bar):**
Rules 2 (breakout weeks counter) and 3 (base length counter) require a manual for-loop to replicate Pine's `var` state variables. The loop tracks:
- `weeks_since_breakout` — resets on crossover above 50WMA
- `breakout_valid_vol` — latches True if volume ≥ 1.5× at crossover
- `weeks_below_50w` / `captured_base_length` — tracks base formation

**Summary dict** returned in `HGResult`:
```python
{
    "weighted_score", "total_weight", "verdict",
    "full_setup", "partial_setup",
    "entry_price_low",   # = 50WMA
    "entry_price_high",  # = 50WMA × (1 + retest_max/100)
    "stop_price",        # = 50WMA × 0.995
    "last_close", "last_date",
    "last_hg_date", "last_hg_entry", "last_hg_gain_pct"
}
```

### 4.4 `app.py` — Streamlit UI Application

The largest file (~1070 lines). Here is a structural breakdown of its components:

#### Page Configuration
```python
st.set_page_config(page_title="Holy Grail — Retest Scanner", layout="wide",
                   initial_sidebar_state="expanded")
```

#### Header Row
- Left: Title "🏆 Holy Grail — Green Cloud Retest Scanner"
- Right: ⚙️ Settings popover with three expandable sections:
  - EMA / MA parameters
  - Rules parameters (RSI length, vol multiplier, retest max, base min)
  - Weights & Thresholds (w1–w6, partial/full thresholds)

#### Sidebar
- Ticker input (default: `ARM`)
- History selector: `["3 Months", "6 Months", "YTD", "1 Year", "2 Years", "5 Years"]` (default: 1 Year)
- Scan button (primary)
- "How to read the chart" legend with colored HTML symbols

#### `render(ticker)` — Main render function
Called once at the bottom of the file: `render(ticker)`. Flow:

1. **Data fetch**: `fetch_weekly`, `fetch_spx_weekly`, `resolve_name`, `fetch_news`
2. **Compute**: `compute(ohlcv, spx_close, settings)` → `res`
3. **Date filter**: Slice `df` by history choice for chart/data display (always fetches 10y for indicator accuracy)
4. **Top verdict banner**: Company name + verdict badge (`COMPLETE SETUP` / `WATCHING` / `NO SETUP`)
5. **Metrics row** (4 columns):
   - Last weekly close
   - Weighted score
   - Gain from HG Signal (gain % since last full setup, with entry date)
   - Entry Range + stop price
6. **Tabs**: `📈 Chart` | `📋 Dashboard` | `🔢 Data` | `🌟 Expert Corner`

#### Chart Tab
- Plotly candlestick chart via `build_chart(df_filtered, ticker, show_cloud)`
- Side-by-side AI panels (two `st.columns(2)`):
  - **Left**: 🧠 AI Technical Analyst (purple gradient card)
  - **Right**: 📰 Current Narrative (orange gradient card)

#### Dashboard Tab
- Rule dashboard table (colored green/red per PASS/FAIL)
- Weighted score summary
- Suggested entry range and stop loss caption

#### Data Tab
- Full DataFrame with columns: open, high, low, close, volume, ma50w, ema5, ema9, ema21, rsi14, pct_above_50w, mansfield_rs, weighted_score, full_setup, partial_setup, blue_square
- CSV download button

#### Expert Corner Tab
- See [Section 9](#9-expert-corner--admin-panel)

#### `build_chart()` function
Builds a Plotly `go.Figure` with:
1. **Candlesticks**: green `#16c784` / red `#ea3943`
2. **EMA cloud** (if enabled): green/red fill between EMA5 and EMA21 via `_add_ema_cloud()`
3. **EMA lines**: EMA21 (blue), EMA9 (teal), EMA5 (green)
4. **50-Week MA**: orange, width=3
5. **Full Setup markers**: dark blue triangle-up at `low * 0.97` with "HG" text (with corresponding weekly green vertical shading), `hoverinfo="skip"`
6. **Partial Setup markers**: yellow circle at `low * 0.98`, `hoverinfo="skip"`
7. **HRR (High Risk Reward) markers**: purple square at `low * 0.96`, `hoverinfo="skip"`
8. Layout: height=640, `plotly_dark` template, horizontal legend, `hovermode="x unified"`

#### `_add_ema_cloud()` function
Splits the EMA5/EMA21 series into contiguous same-sign runs and draws each as a `fill="tonexty"` band. Green fill (`rgba(22,199,132,0.22)`) when EMA5 > EMA21, red fill (`rgba(234,57,67,0.22)`) otherwise. Runs are extended by one bar on the right to prevent visible gaps at crossovers.

### 4.5 `watchlist.json` — Persistent Watchlist Data

JSON array of objects:
```json
[
  {
    "ticker": "AAPL",
    "date_added": "2026-06-19",
    "price_added": 296.0,
    "verdict": "BUY",
    "commentary": "INTC partnership is the catalyst"
  }
]
```
Verdicts: `BUY` | `WATCH` | `HOLD` | `AVOID`

### 4.6 `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential curl software-properties-common git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
RUN chmod +x run.sh
ENTRYPOINT ["./run.sh"]
```

### 4.7 `run.sh`

```bash
#!/bin/bash
PORT=${PORT:-8501}
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

### 4.8 `.dockerignore`

Excludes: `.git`, `__pycache__`, `*.pyc`, `.python-version`, `.venv`, `venv`, `env`, `.streamlit/config.toml`, `.streamlit/secrets.toml`

### 4.9 `.gitignore`

Excludes: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `.DS_Store`, `*.csv`, `.streamlit/secrets.toml`

---

## 5. The 6 Holy Grail Rules (Indicator Logic)

| # | Rule | Weight | PASS Condition |
|---|---|---|---|
| 1 | **Retest Zone** | 0.15 | Price is 0–15% above the 50WMA |
| 2 | **Breakout + Volume** | 0.10 | Price crossed above 50WMA ≥1 week ago AND the crossover bar had volume ≥ 1.5× the 10-week average |
| 3 | **Base Length** | 0.10 | The stock spent ≥ 15 weeks below 50WMA before the breakout |
| 4 | **Green Cloud Birth** | 0.25 | EMA5 recently crossed above EMA9 (within 3 bars), EMAs are compressed (< 2% apart), price is above all 3 EMAs, and the candle is green |
| 5 | **Mansfield RS** | 0.30 | Mansfield Relative Strength vs S&P 500 is > 0 (stock outperforming the index on a 52-week basis) |
| 6 | **RSI > 50** | 0.10 | 14-period RSI is above 50 |

**Scoring:**
- `weighted_score = sum(rule_passed × weight)`
- **COMPLETE SETUP** (Full): score ≥ 0.70
- **WATCHING** (Partial): Rule 1 passes AND score ≥ 0.35
- **NO SETUP**: everything else

**Entry / Exit:**
- **Entry range**: 50WMA to 50WMA × 1.15 (the retest zone)
- **Stop loss**: 50WMA × 0.995 (on a weekly closing basis)

---

## 6. Chart Markers & Visual Signals

| Marker | Symbol | Color | Y Position | Meaning |
|---|---|---|---|---|
| Full Setup (HG) | `triangle-up` + "HG" text (green vertical shade on chart) | `#1d4ed8` (dark blue) | `low × 0.97` | Complete Holy Grail setup — best entry |
| Partial Setup | `circle` | `#ffd600` (amber) | `low × 0.98` | Watching — medium confidence |
| HRR (High Risk Reward) | `square` | `#e040fb` (neon purple) | `low × 0.96` | Red-to-green EMA cloud flip — high risk/reward |

All three markers have `hoverinfo="skip"` to suppress incorrect price tooltips (since Y positions are offset from actual candle data).

---

## 7. AI Technical Analyst Feature

**Function**: `generate_ai_summary(ticker, name, res, settings) → (html, source_label)`

**Flow:**
1. Collects all rule statuses, weighted score, verdict, entry/exit prices
2. Builds a prompt asking for a concise HTML-formatted executive technical summary
3. Tries Gemini API (`gemini-2.5-flash`) via REST if `GEMINI_API_KEY` is in `st.secrets`
4. Tries OpenAI API (`gpt-4o-mini`) via REST if `OPENAI_API_KEY` is in `st.secrets`
5. Falls back to a programmatic rules-based natural language generator with 3 sections:
   - **Setup Status**: Complete/Watching/None with score context
   - **Technical Breakdown**: 50WMA proximity, volume, Mansfield RS, RSI analysis
   - **Execution Strategy**: Entry range and stop loss with rationale

**UI**: Rendered in a purple gradient card (`rgba(224, 64, 251, 0.08)` → transparent) with a source badge.

---

## 8. Current Narrative (News Catalyst) Feature

**Function**: `generate_catalyst_narrative(ticker, name, news_items) → (html, source_label)`

**Flow:**
1. Parses yfinance news (new nested `content` sub-dict format):
   - Title: `item["content"]["title"]`
   - Publisher: `item["content"]["provider"]["displayName"]`
   - Link: `item["content"]["canonicalUrl"]["url"]`
   - Date: `item["content"]["pubDate"]` (ISO string)
2. Filters to articles published within the last **14 days (2 weeks)**
3. Limits to top 5 items for the AI prompt
4. Tries Gemini / OpenAI REST APIs (same pattern as Technical Analyst)
5. Falls back to a bulleted list of top 3 headlines with source links

**UI**: Rendered in an orange gradient card (`rgba(255, 145, 0, 0.08)` → transparent) side-by-side with the Technical Analyst.

---

## 9. Expert Corner & Admin Panel

### Expert Corner Display
- Rendered via `st.components.v1.html()` (bypasses Streamlit's markdown parser for complex HTML)
- Table columns: Date Added | Ticker | Price Added | Current Price | Verdict | Gain/Loss
- Tickers are clickable links (`target="_parent"` targeting the URL query parameter `?ticker=XYZ`), which reloads the page on the default Chart tab for the clicked stock
- Current prices fetched live from yfinance (`fetch_weekly(ticker, period="1mo")`)
- Verdicts are color-coded badges with hover tooltips showing admin commentary
- Sorted descending by `date_added` (most recent first)

### Verdict Colors
| Verdict | Color |
|---|---|
| BUY | `#00e676` (green) |
| WATCH | `#ffd600` (yellow) |
| HOLD | `#38b6ff` (blue) |
| AVOID | `#ea3943` (red) |

### Admin Panel
- Protected by password (`st.secrets["admin_password"]`, fallback: `"MakeUsRich25%"`)
- **Add Ticker**: Symbol, date, auto-fetch price button, verdict selector (BUY/WATCH/HOLD/AVOID), commentary text area
- **Remove Ticker**: Multi-select of existing tickers
- Persistence status indicator (GitHub active vs local-only)

### GitHub-Backed Persistence
The watchlist persists across Streamlit Cloud re-deploys by committing `watchlist.json` directly to the GitHub repo via the GitHub Contents API:

- `_gh_cfg()` — reads `GITHUB_TOKEN`, `GITHUB_REPO`, `GITHUB_BRANCH`, `GITHUB_FILE_PATH` from `st.secrets`
- `load_wl()` — GET `/repos/{repo}/contents/{path}`, base64-decode the content
- `save_wl(data)` — GET current SHA, then PUT with updated content + SHA
- Falls back to local `watchlist.json` file read/write when secrets are not configured

---

## 10. Streamlit Cloud Secrets Configuration

Add these in **Streamlit Cloud → App Settings → Secrets** (TOML format):

```toml
# Admin password for watchlist management
admin_password = "your_admin_password_here"

# GitHub persistence for watchlist.json
GITHUB_TOKEN     = "ghp_your_fine_grained_pat_here"
GITHUB_REPO      = "ravichandran-urmila/holygrail-app"
GITHUB_BRANCH    = "master"
GITHUB_FILE_PATH = "watchlist.json"

# AI features (optional — falls back to programmatic generator)
GEMINI_API_KEY   = "your_gemini_api_key_here"
# OPENAI_API_KEY = "sk-your_openai_api_key_here"
```

**GitHub Token**: Generate at GitHub → Settings → Developer settings → Fine-grained personal access tokens. Grant **Contents: Read & write** permission on the repository.

---

## 11. Deployment Instructions

### Option A: Streamlit Community Cloud (Recommended, Free)

1. Push the repo to GitHub:
   ```bash
   cd holygrail_app
   git init
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git add .
   git commit -m "Initial commit"
   git branch -M master
   git push -u origin master
   ```
2. Go to [share.streamlit.io](https://share.streamlit.io/)
3. Sign in with GitHub → New App → select your repo, branch `master`, main file `app.py`
4. Click Deploy
5. Add Secrets in App Settings (see Section 10)

### Option B: Docker (Render, Fly.io, Railway)

```bash
cd holygrail_app
docker build -t holygrail .
docker run -p 8501:8501 holygrail
```

For cloud platforms, the `run.sh` script reads the `$PORT` environment variable automatically.

### Option C: Local Development

```bash
cd holygrail_app
pip install -r requirements.txt
streamlit run app.py
```

---

## 12. Color Palette & Design Tokens

| Purpose | Color | Hex |
|---|---|---|
| Full Setup signals | Dark blue | `#1d4ed8` |
| Full Setup highlighting | Soft green shade | `rgba(22,199,132,0.12)` |
| Bullish candles | Green | `#16c784` |
| Bearish candles / Stop loss | Red | `#ea3943` |
| Partial Setup / Watching | Amber | `#ffd600` |
| HRR (High Risk Reward) | Neon purple | `#e040fb` |
| 50-Week MA line | Orange | `orange` |
| HOLD verdict | Light blue | `#38b6ff` |
| EMA21 line | Blue | `rgba(41,98,255,0.7)` |
| EMA9 line | Teal | `rgba(0,170,170,0.7)` |
| EMA5 line | Green | `rgba(0,200,120,0.85)` |
| EMA cloud (bullish) | Green fill | `rgba(22,199,132,0.22)` |
| EMA cloud (bearish) | Red fill | `rgba(234,57,67,0.22)` |
| AI Technical Analyst card | Purple gradient | `rgba(224,64,251,0.08)` |
| Current Narrative card | Orange gradient | `rgba(255,145,0,0.08)` |
| No Setup verdict | Gray | `#888888` |

---

## 13. Known Pitfalls & Gotchas

### yfinance News API Format Change
The `.news` attribute now returns items with a nested `content` sub-dict:
```
item["content"]["title"]           # was: item["title"]
item["content"]["pubDate"]         # was: item["providerPublishTime"] (unix)
item["content"]["provider"]["displayName"]  # was: item["publisher"]
item["content"]["canonicalUrl"]["url"]      # was: item["link"]
```
Always unwrap `content = item.get("content", item)` for backward compatibility.

### Streamlit Markdown vs Raw HTML
- **Never** use `st.markdown()` with indented HTML blocks — Streamlit's markdown parser will render them as code blocks
- For complex HTML tables, use `st.components.v1.html()` instead
- For inline HTML (bold, spans), use `st.markdown(..., unsafe_allow_html=True)` with minimal indentation

### Streamlit Secrets Locally
- Wrap all `st.secrets` access in `try/except` blocks
- Locally, there is no `.streamlit/secrets.toml` file, so `st.secrets` will raise `FileNotFoundError`
- Fallback pattern: `try: val = st.secrets["KEY"] except: val = "default"`

### Git Rebase Before Push
- The admin panel's `save_wl()` commits `watchlist.json` directly to GitHub via API
- This means `origin/master` may be ahead of your local branch after an admin saves
- **Always** run `git pull --rebase origin master` before `git push` to avoid rejection

### Indicator Accuracy
- The app always fetches **10 years** of data internally (`period="10y"`) even when the user selects a shorter history range
- This ensures the 50-week MA and Mansfield RS (52-week) compute accurately from the first visible bar
- The chart and data table are then **filtered** to the selected date range for display only

### Marker Hover Suppression
- Chart markers (HG triangle, yellow dot, HRR square) use offset Y positions (`low * 0.97/0.98/0.96`) to avoid overlapping candles
- Because of this, their hover tooltips showed wrong prices
- All three traces use `hoverinfo="skip"` to suppress tooltips while remaining visible

---

## Quick Start Rebuild Checklist

```
□ Create project directory
□ Create requirements.txt with 6 packages
□ Create data.py with 4 cached functions (fetch_weekly, fetch_spx_weekly, resolve_name, fetch_news)
□ Create indicator.py with HGSettings dataclass, 5 TA helpers, compute() function
□ Create app.py:
  □ Page config (wide layout, expanded sidebar)
  □ Header with settings popover (EMA/MA, Rules, Weights sections)
  □ Sidebar with ticker input, history selector, scan button, chart legend
  □ render() function:
    □ Data fetching (4 calls)
    □ Indicator computation
    □ Date filtering for display
    □ Verdict banner with styled badge
    □ 4-column metrics row (close, score, gain from HG, entry range)
    □ 4 tabs: Chart, Dashboard, Data, Expert Corner
    □ Expert Corner tab: HTML table + admin panel
    □ Dashboard tab: Rules table + score summary
    □ Data tab: Raw DataFrame + CSV download
  □ generate_ai_summary() — Gemini/OpenAI/fallback
  □ generate_catalyst_narrative() — news parsing + Gemini/OpenAI/fallback
  □ build_chart() — candlestick + EMA cloud + MA + signal markers
  □ _add_ema_cloud() — segmented fill between EMA5 and EMA21
  □ render(ticker) call at bottom
□ Create watchlist.json (empty array: [])
□ Create Dockerfile, run.sh, .dockerignore, .gitignore
□ Initialize git, push to GitHub
□ Deploy to Streamlit Cloud
□ Configure Secrets (admin_password, GITHUB_TOKEN/REPO/BRANCH/FILE_PATH, GEMINI_API_KEY)
```
