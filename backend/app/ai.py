"""AI analyst panels: technical, fundamental, and catalyst-narrative summaries.

Providers (Gemini -> OpenAI -> HuggingFace) are used when the matching env key
is present; otherwise a deterministic local template is returned. Every function
returns (html, source_label).
"""

from __future__ import annotations

import html as _html
import os
import re
from datetime import datetime, timezone, timedelta

import numpy as np
import requests

from . import data as datalib

HF_MODELS = [
    "Qwen/Qwen2.5-7B-Instruct",
    "google/gemma-2-2b-it",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "microsoft/Phi-3-mini-4k-instruct",
    "HuggingFaceH4/zephyr-7b-beta",
]


def _keys():
    return (
        os.environ.get("GEMINI_API_KEY"),
        os.environ.get("OPENAI_API_KEY"),
        os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY"),
    )


def _clean_html_response(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    m = re.search(r"```(?:html)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        text = m.group(1).strip()
    else:
        m2 = re.search(r"(<[a-zA-Z]+.*?>.*)", text, re.DOTALL)
        if m2:
            text = m2.group(1).strip()
    return text.replace("```", "").strip()


def _call_llm(prompt: str, label_prefix: str = "") -> tuple[str, str] | None:
    gemini_key, openai_key, hf_token = _keys()

    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 300, "temperature": 0.4},
                },
                timeout=8,
            )
            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return _clean_html_response(text), f"{label_prefix}Gemini 2.5 Flash"
        except Exception:
            pass

    if openai_key:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.4,
                },
                timeout=8,
            )
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"].strip()
                if text:
                    return _clean_html_response(text), f"{label_prefix}GPT-4o-mini"
        except Exception:
            pass

    if hf_token:
        for model in HF_MODELS:
            try:
                resp = requests.post(
                    f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 250,
                        "temperature": 0.4,
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    text = resp.json()["choices"][0]["message"]["content"].strip()
                    if text:
                        return _clean_html_response(text), f"HF ({model.split('/')[-1]})"
            except Exception:
                pass
    return None


# --------------------------------------------------------------------------
# Technical
# --------------------------------------------------------------------------
def technical_summary(ticker: str, name: str, res, settings) -> tuple[str, str]:
    df = res.df
    sm = res.summary
    last_row = df.iloc[-1]
    last_close = sm["last_close"]
    weighted_score = sm["weighted_score"]
    total_weight = sm["total_weight"]
    verdict = sm["verdict"]
    entry_low, entry_high, stop_price = sm["entry_price_low"], sm["entry_price_high"], sm["stop_price"]

    rules_text = "\n".join(f"- {r}: {s} ({v})" for r, s, v, _ in res.dashboard)

    hg_weeks_ago = hg_close_price = None
    if sm.get("last_hg_date") is not None:
        idx_list = list(df.index)
        try:
            pos = idx_list.index(sm["last_hg_date"])
            hg_weeks_ago = len(idx_list) - 1 - pos
            hg_close_price = float(df.loc[sm["last_hg_date"], "close"])
        except ValueError:
            pass

    above_50wma = (
        last_close >= last_row["ma50w"]
        if ("ma50w" in last_row and not np.isnan(last_row["ma50w"]))
        else False
    )

    if hg_weeks_ago is not None and hg_close_price is not None:
        pct = ((last_close - hg_close_price) / hg_close_price) * 100.0
        hg_prompt = f"A COMPLETE Holy Grail setup was triggered {hg_weeks_ago} week(s) ago (week close ${hg_close_price:.2f}). "
        if pct <= 15.0 and above_50wma:
            hg_prompt += f"Current close (${last_close:.2f}) is {pct:.1f}% from setup close, within the 15% range and above the 50WMA — prime buying zone."
        elif above_50wma:
            hg_prompt += f"Current close (${last_close:.2f}) is {pct:.1f}% above setup close, exceeding the 15% range (extended)."
        else:
            hg_prompt += "Price has since dropped below the 50WMA, invalidating the setup."
    else:
        hg_prompt = "No COMPLETE Holy Grail setup has been triggered in the history."

    prompt = f"""You are a professional stock market technical analyst. Write a highly concise, structured, non-wordy executive summary analyzing {name} ({ticker}) based on the Holy Grail setup rules.

Holy Grail Setup Status:
- {hg_prompt}
- Current Setup Verdict: {verdict}
- Latest Close: ${last_close:.2f}
- Weighted Score: {weighted_score:.2f} / {total_weight:.2f}

Rules breakdown:
{rules_text}

Entry/Exit Strategy:
- Suggested Entry Range: ${entry_low:.2f} to ${entry_high:.2f} (50WMA to +{settings.retest_max:.1f}%)
- Suggested Stop Loss: ${stop_price:.2f} (50WMA * 0.995 on a weekly closing basis)

CRITICAL INSTRUCTIONS:
1. Be concise (short bulleted points or tight sentences).
2. Acknowledge the most recent Holy Grail setup and whether it's still a good time to buy.
3. Format in raw HTML using <p>, <strong>, <ul>, <li>. No markdown/code blocks. Under 120 words."""

    result = _call_llm(prompt)
    if result:
        return result

    # Local template fallback
    if hg_weeks_ago is not None and hg_close_price is not None:
        pct = ((last_close - hg_close_price) / hg_close_price) * 100.0
        if above_50wma and pct <= 15.0:
            history_html = f"<li>🟢 <strong>Holy Grail Buy Zone</strong>: A complete buy setup occurred <strong>{hg_weeks_ago} week(s) ago</strong> (HG close ${hg_close_price:.2f}). Price is within the 15% range (<strong>{pct:.1f}%</strong> above) and above the 50WMA — a <strong>prime buying zone</strong>.</li>"
        elif above_50wma:
            history_html = f"<li>⚠️ <strong>Extended Price</strong>: A complete buy setup occurred <strong>{hg_weeks_ago} week(s) ago</strong> (HG close ${hg_close_price:.2f}). Price is <strong>{pct:.1f}%</strong> above the setup close (extended).</li>"
        else:
            history_html = f"<li>❌ <strong>Setup Invalidated</strong>: A setup occurred <strong>{hg_weeks_ago} week(s) ago</strong> but price has since dropped below the 50WMA.</li>"
    else:
        history_html = "<li>⚠️ <strong>No Active Setup</strong>: No complete Holy Grail setup in history.</li>"

    status_title = {"COMPLETE SETUP": "🚀 Complete Buy Setup", "WATCHING": "👀 On Close Watch"}.get(
        verdict, "⚠️ No Active Setup"
    )
    retest_val = last_row["pct_above_50w"]
    if np.isnan(retest_val):
        retest_desc = "Insufficient history for 50WMA."
    elif retest_val >= 0:
        retest_desc = f"Price is <strong>{retest_val:.1f}%</strong> above the 50WMA (${last_row['ma50w']:.2f})."
    else:
        retest_desc = f"Price is <strong>{-retest_val:.1f}%</strong> below the 50WMA (${last_row['ma50w']:.2f})."
    vol_desc = "Strong volume breakout confirmed." if bool(last_row["rule2_breakout"]) else "No recent volume breakout."
    rs_desc = (
        "Relative strength is bullish (Mansfield RS > 0)."
        if (("mansfield_rs" in last_row and not np.isnan(last_row["mansfield_rs"])) and bool(last_row["rule5_mansfield"]))
        else "Underperforming the S&P 500."
    )
    html = (
        f"<p><strong>{status_title}</strong> ({weighted_score:.2f}/{total_weight:.2f}):</p>"
        f"<ul>{history_html}"
        f"<li>📊 <strong>Trend</strong>: {retest_desc} {vol_desc} {rs_desc}</li>"
        f"<li>🎯 <strong>Strategy</strong>: Buy between <strong>${entry_low:.2f} and ${entry_high:.2f}</strong>. Stop-loss at <strong>${stop_price:.2f}</strong> on a weekly close.</li>"
        f"</ul>"
    )
    return html, "Local Expert System"


# --------------------------------------------------------------------------
# Fundamental
# --------------------------------------------------------------------------
def fundamental_summary(ticker: str, name: str) -> tuple[str, str]:
    data = datalib.fetch_financial_info(ticker)
    info = data.get("info") or {}
    fcf_history = data.get("fcf_history") or []

    ev_ebitda = info.get("enterpriseToEbitda")
    trailing_pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    ps = info.get("priceToSalesTrailing12Months")
    rev_growth = info.get("revenueGrowth")
    forward_ps = ps / (1.0 + rev_growth) if (ps is not None and rev_growth is not None) else None
    peg = info.get("pegRatio")
    fcf = info.get("freeCashflow")
    mcap = info.get("marketCap")

    def f(v):
        return f"{v:.2f}" if v is not None else "N/A"

    p_fcf = None
    p_fcf_desc = "N/A"
    if mcap and fcf:
        p_fcf = mcap / fcf
        p_fcf_desc = f"{p_fcf:.2f}"
    elif fcf and fcf < 0:
        p_fcf_desc = "Negative FCF"

    fcf_growth_pct = None
    fcf_growth_desc = "N/A"
    if len(fcf_history) >= 2:
        v0, v1 = fcf_history[0].get("val"), fcf_history[1].get("val")
        if v0 is not None and v1 is not None and v1 != 0:
            fcf_growth_pct = ((v0 - v1) / abs(v1)) * 100.0
            fcf_growth_desc = f"{fcf_growth_pct:+.1f}%"

    p_fcf_growth_desc = "N/A"
    if p_fcf is not None and fcf_growth_pct is not None and fcf_growth_pct > 0:
        p_fcf_growth_desc = f"{p_fcf / fcf_growth_pct:.2f}"

    prompt = f"""You are a professional fundamental stock market analyst. Write a highly concise, structured executive summary analyzing the fundamental health of {name} ({ticker}).

Key Financial Metrics:
- Trailing PE: {f(trailing_pe)}
- Forward PE: {f(forward_pe)}
- Trailing PS: {f(ps)}
- Forward PS: {f(forward_ps)}
- PEG Ratio: {f(peg)}
- EV/EBITDA: {f(ev_ebitda)}
- Price to Free Cash Flow (P/FCF): {p_fcf_desc}
- YoY Free Cash Flow Growth: {fcf_growth_desc}
- Price to FCF Growth Ratio: {p_fcf_growth_desc}

CRITICAL INSTRUCTIONS:
1. One intro paragraph then a <ul> with EXACTLY 3 bullets: 📊 Valuation, 💰 Cash Flow, 💡 Context.
2. Under 130 words.
3. Raw HTML using <p>, <strong>, <ul>, <li>. No markdown/code blocks."""

    result = _call_llm(prompt, label_prefix="")
    if result:
        return result

    mcap_desc = f"${mcap/1e9:.1f}B" if mcap else "N/A"
    valuation_signals = []
    if ev_ebitda is not None:
        if ev_ebitda < 12.0:
            valuation_signals.append("EV/EBITDA is low/undervalued (<12)")
        elif ev_ebitda > 25.0:
            valuation_signals.append("EV/EBITDA is premium-priced (>25)")
    if forward_pe is not None:
        if forward_pe < 15.0:
            valuation_signals.append("Forward PE suggests value pricing (<15)")
        elif forward_pe > 35.0:
            valuation_signals.append("Forward PE is growth-priced (>35)")
    if valuation_signals:
        valuation_health = f"Valuation profile: {', '.join(valuation_signals)}."
        valuation_health += (
            " Ratios suggest the market has priced in a significant growth premium."
            if (forward_pe and forward_pe > 35.0)
            else " Ratios indicate defensive value pricing relative to assets and earnings."
        )
    else:
        valuation_health = "Valuation ratios represent a standard market-average pricing profile."

    growth_verdict = "YoY Free Cash Flow growth is negative or unavailable, suggesting near-term operational friction."
    if fcf_growth_pct is not None:
        if fcf_growth_pct > 20.0:
            growth_verdict = f"YoY Free Cash Flow growth is very strong at <strong>{fcf_growth_desc}</strong>, indicating a powerful, expanding business model."
        elif fcf_growth_pct > 0:
            growth_verdict = f"YoY Free Cash Flow growth is healthy at <strong>{fcf_growth_desc}</strong>, reflecting steady business scale."

    html = (
        f"<p><strong>Valuation Snapshot</strong> (Market Cap: {mcap_desc}):</p>"
        f"<ul>"
        f"<li>📊 <strong>Valuation</strong>: PE: <strong>{f(trailing_pe)}</strong> (T) / <strong>{f(forward_pe)}</strong> (F) | PS: <strong>{f(ps)}</strong> / <strong>{f(forward_ps)}</strong> | PEG: <strong>{f(peg)}</strong> | EV/EBITDA: <strong>{f(ev_ebitda)}</strong>.</li>"
        f"<li>💰 <strong>Cash Flow</strong>: P/FCF: <strong>{p_fcf_desc}</strong> | Growth: <strong>{fcf_growth_desc}</strong>. {growth_verdict}</li>"
        f"<li>💡 <strong>Context</strong>: {valuation_health}</li>"
        f"</ul>"
    )
    return html, "Local Expert System"


# --------------------------------------------------------------------------
# Catalyst narrative
# --------------------------------------------------------------------------
def catalyst_narrative(ticker: str, name: str, news_items: list) -> tuple[str, str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    valid_news = []
    for item in news_items or []:
        content = item.get("content", item)
        title = content.get("title")
        if not title:
            continue
        provider = content.get("provider") or {}
        publisher = (provider.get("displayName") if isinstance(provider, dict) else None) or content.get("publisher") or "Unknown"
        canon = content.get("canonicalUrl") or {}
        click = content.get("clickThroughUrl") or {}
        link = (
            (canon.get("url") if isinstance(canon, dict) else None)
            or (click.get("url") if isinstance(click, dict) else None)
            or content.get("link")
            or "#"
        )
        pub_date_str = content.get("pubDate")
        pub_ts = content.get("providerPublishTime")
        if pub_date_str:
            try:
                if datetime.fromisoformat(pub_date_str.replace("Z", "+00:00")) < cutoff:
                    continue
            except Exception:
                pass
        elif pub_ts:
            try:
                if float(pub_ts) < cutoff.timestamp():
                    continue
            except Exception:
                pass
        valid_news.append({"title": title, "publisher": publisher, "link": link})

    news_subset = valid_news[:5]
    if not news_subset:
        return (
            f"<p>No recent news catalysts were found for <strong>{_html.escape(name)} ({_html.escape(ticker)})</strong>. "
            "The narrative is currently driven by standard macroeconomic updates and sector trends.</p>",
            "Local System",
        )

    news_text = "".join(f'{i+1}. "{n["title"]}" (published by {n["publisher"]})\n' for i, n in enumerate(news_subset))
    prompt = f"""You are a professional financial journalist and stock market catalyst analyst.
Analyze the following recent news headlines for {name} ({ticker}) and synthesize them into a concise unified "current narrative" summary (max 120 words).
Identify the key catalyst potentially moving the stock.

Recent News Headlines for {ticker}:
{news_text}

CRITICAL FORMATTING INSTRUCTIONS:
Raw HTML (using <p>, <strong>, <br/>). No <html>/<body>, no code blocks. Under 120 words."""

    result = _call_llm(prompt)
    if result:
        return result

    html = f"<p>Recent news headlines indicating potential catalysts for <strong>{_html.escape(name)} ({_html.escape(ticker)})</strong>:</p><ul style='margin-left:15px;padding-left:0;'>"
    for n in valid_news[:3]:
        safe_title = _html.escape(n["title"])
        safe_pub = _html.escape(n["publisher"])
        safe_link = _html.escape(n["link"], quote=True)
        html += (
            f"<li style='margin-bottom:8px;'><a href='{safe_link}' target='_blank' rel='noopener noreferrer' "
            f"style='color:#ff9100;text-decoration:underline;'>{safe_title}</a> "
            f"<span style='color:rgba(255,255,255,0.5);font-size:0.85rem;'>({safe_pub})</span></li>"
        )
    html += "</ul>"
    return html, "Recent Yahoo News"
