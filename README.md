# 🏆 Holy Grail — Green Cloud Retest Scanner (app)

This Streamlit application implements the **Holy Grail — Green Cloud Retest** trading system.

## What is the Holy Grail Setup?

The **Holy Grail** is a weekly-timeframe trend-following and momentum breakout system designed to identify high-probability entry points for leading stocks. It scans for stocks that have built a long accumulation base and are beginning a major markup phase.

The system evaluates **6 key rules** on the weekly chart:
1. **Retest Zone**: Price pulls back to the rising 50-week Moving Average (50WMA) — within a 0% to 10% range.
2. **Breakout + Volume**: A recent breakout above the 50WMA accompanied by above-average weekly volume.
3. **Base Length**: Prior to breakout, the price spent at least 15 weeks consolidating below the 50WMA (signaling accumulation).
4. **Green Cloud**: The short-term EMAs (5, 9, 21) are compressed, above the 50WMA, and in a green alignment.
5. **Mansfield Relative Strength (RS)**: Outperformance against the S&P 500 (`^GSPC`), showing market leadership.
6. **Momentum (RSI > 50)**: Standard weekly momentum confirmation.

Each rule has a specific weight. The sum of these weights produces a **Weighted Score** (up to 1.0).

---

## Optimal Entry Strategy

* **Full Setup (Score ≥ 0.70)**: The ideal, fully-validated breakout and retest signal.
* **Watching / Close to Full Setup (Score ≥ 0.35)**: **Anything close to a full setup represents an excellent entry point.** Because the stock is actively in the 50WMA retest zone, entering during a partial setup allows you to buy the stock closer to the structural support level (the 50WMA), resulting in a tighter stop-loss and a higher reward-to-risk ratio.

## How to Read the Chart

* **▲ Weekly Green Triangle (HG)**: Indicates a **Full Holy Grail Setup** and the best time to enter a stock.
* **🟡 Yellow Dot**: Indicates a **Partial Setup** representing a medium confidence level to enter a stock.
* **■ Purple Square**: Indicates Red to Green EMA cloud flip (crossover), representing a **high risk high reward** entry week.

## Architecture (v2 — React + FastAPI)

The app has been rebuilt from Streamlit into a scalable two-tier application. The
validated Pine-Script indicator math is **reused unchanged** on the Python side; a
beautiful React + Tailwind UI renders it via a TradingView-grade chart.

```
holygrail-app/
├── backend/                 FastAPI service (Python)
│   └── app/
│       ├── indicator.py     ← faithful Pine port (6 rules + scoring), reused verbatim
│       ├── data.py          yfinance weekly data layer (streamlit-free, TTL cached)
│       ├── scan_service.py  turns indicator output into chart-ready JSON
│       ├── watchlist.py     Expert Corner storage (GitHub-backed + local fallback)
│       ├── ai.py            AI analyst panels (Gemini/OpenAI/HF → local templates)
│       └── main.py          REST API (/api/scan, /api/watchlist, /api/guide, …)
├── frontend/                React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── components/Chart.tsx    lightweight-charts candlesticks
│       ├── lib/bandSeries.ts       custom green/red EMA-cloud band series
│       └── pages/                  Scanner · Guide · ExpertCorner
└── app.py, indicator.py, …  legacy Streamlit app (kept for reference)
```

## Run (development)

One command runs both tiers:

```bash
./dev.sh
```

…or run them separately:

```bash
# Backend  →  http://localhost:8000
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend →  http://localhost:5173  (proxies /api to the backend)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and search a ticker (e.g. `AAPL`, `NVDA`, `ARM`).

## Configuration

Copy `backend/.env.example` → `backend/.env` (or set env vars) to enable:

- `ADMIN_EMAIL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` — configures temporary email PIN auth for Expert Corner writes. (Local development falls back to static `ADMIN_PASSWORD` or `holygrail`).
- `GEMINI_API_KEY` / `OPENAI_API_KEY` / `HF_TOKEN` — richer AI panels (optional;
  falls back to deterministic local templates).
- `GITHUB_TOKEN` / `GITHUB_REPO` / … — persist the watchlist to GitHub so edits
  survive redeploys.

## Deploy

- **Backend:** `backend/Dockerfile` builds a container serving on `:8000`.
- **Frontend:** `npm run build` emits a static `dist/` (any static host / CDN).
  Set `VITE_API_BASE` to the backend URL if not co-hosted behind one origin.

## Notes / caveats

- **Weekly only** — the original system is designed for weekly charts; the app
  fetches `interval="1wk"`.
- yfinance is unofficial and occasionally rate-limits; data is cached for 1h.
- EMA/RSI use standard `ewm`/Wilder formulas that match Pine closely. Tiny
  float differences vs TradingView are possible at the far-left edge of history.
- **Educational tool, not financial advice.**
