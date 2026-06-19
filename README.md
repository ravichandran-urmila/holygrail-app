# 🏆 Holy Grail — Green Cloud Retest Scanner (app)

A Streamlit app that lets you **search a ticker**, pulls up its **weekly candlestick
chart**, and overlays the **Holy Grail — Green Cloud Retest** indicator (ported 1:1
from the TradingView Pine v6 script in `../core`).

## Why it doesn't "use the TradingView API"

TradingView has **no public API** for pulling raw market data or for running a
*custom* Pine Script indicator inside a third-party app. Their embeddable chart
widgets only support TradingView's *built-in* indicators. So this app instead:

1. **Re-implements** the indicator logic in Python (`indicator.py`) — exactly
   matching the Pine rules, weighted score, and dashboard.
2. Pulls **weekly OHLCV** from Yahoo Finance via `yfinance` (free, no key).
3. Renders candlesticks + EMA cloud + 50WMA + signal markers with Plotly, and
   shows the same dashboard the Pine script draws on TradingView.

The S&P 500 benchmark for Mansfield RS (`SPX` in Pine) maps to `^GSPC` on Yahoo.

## Files

| File | Purpose |
|------|---------|
| `indicator.py` | Faithful port of the Pine logic (6 rules + scoring + dashboard) |
| `data.py`      | yfinance weekly data layer (ticker + ^GSPC) |
| `app.py`       | Streamlit UI: search, chart, dashboard, raw data |

## Run

```bash
cd holygrail_app
python3.10 -m pip install -r requirements.txt     # first time only
python3.10 -m streamlit run app.py
```

Then open the URL it prints (default http://localhost:8501), type a ticker
(e.g. `AAPL`, `NVDA`, `SPY`) in the sidebar, and press **Scan**.

## Notes / caveats

- **Weekly only** — the original system is designed for weekly charts; the app
  fetches `interval="1wk"`.
- yfinance is unofficial and occasionally rate-limits; data is cached for 1h.
- EMA/RSI use standard `ewm`/Wilder formulas that match Pine closely. Tiny
  float differences vs TradingView are possible at the far-left edge of history.
- **Educational tool, not financial advice.**
