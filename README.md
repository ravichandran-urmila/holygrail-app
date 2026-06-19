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
* **■ Blue Square**: Indicates Red to Green EMA cloud flip (crossover), representing a **high risk high reward** entry week.

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
