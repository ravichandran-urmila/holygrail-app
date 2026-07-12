"""Expert Corner watchlist storage: GitHub-backed with a local-file fallback."""

from __future__ import annotations

import base64
import json
import os

import requests

from . import data as datalib

_GH_API = "https://api.github.com"

# Local fallback: check env override, then search up from this file.
_LOCAL_PATH = os.environ.get("WATCHLIST_PATH", "")
if not _LOCAL_PATH:
    _dir = os.path.dirname(__file__)
    for _up in [os.path.join(_dir, ".."), os.path.join(_dir, "..", "..")]:
        _candidate = os.path.join(_up, "watchlist.json")
        if os.path.exists(_candidate):
            _LOCAL_PATH = _candidate
            break
    else:
        _LOCAL_PATH = os.path.join(_dir, "..", "..", "watchlist.json")



def _gh_cfg():
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPO", "")
    branch = os.environ.get("GITHUB_BRANCH", "master")
    path = os.environ.get("GITHUB_FILE_PATH", "watchlist.json")
    if token and repo:
        return token, repo, branch, path
    return None


def github_enabled() -> bool:
    return _gh_cfg() is not None


def load() -> list[dict]:
    cfg = _gh_cfg()
    if cfg:
        token, repo, branch, path = cfg
        try:
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            r = requests.get(
                f"{_GH_API}/repos/{repo}/contents/{path}?ref={branch}",
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200:
                raw = base64.b64decode(r.json()["content"]).decode("utf-8")
                data = json.loads(raw)
                return data.get("items", []) if isinstance(data, dict) else data
        except Exception:
            pass

    if os.path.exists(_LOCAL_PATH):
        try:
            with open(_LOCAL_PATH) as f:
                data = json.load(f)
                return data.get("items", []) if isinstance(data, dict) else data
        except Exception:
            pass
    return []


def save(items: list[dict]) -> bool:
    payload_str = json.dumps(items, indent=2)
    cfg = _gh_cfg()
    if cfg:
        token, repo, branch, path = cfg
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        try:
            r_get = requests.get(
                f"{_GH_API}/repos/{repo}/contents/{path}?ref={branch}",
                headers=headers,
                timeout=10,
            )
            sha = r_get.json().get("sha", "") if r_get.status_code == 200 else ""
            body = {
                "message": "chore: update watchlist via admin panel",
                "content": base64.b64encode(payload_str.encode()).decode(),
                "branch": branch,
            }
            if sha:
                body["sha"] = sha
            r_put = requests.put(
                f"{_GH_API}/repos/{repo}/contents/{path}",
                headers=headers,
                json=body,
                timeout=15,
            )
            return r_put.status_code in (200, 201)
        except Exception:
            return False

    try:
        with open(_LOCAL_PATH, "w") as f:
            f.write(payload_str)
        return True
    except Exception:
        return False


def with_live_prices(items: list[dict]) -> list[dict]:
    """Attach current price + gain to each watchlist row."""
    enriched = []
    for item in items:
        ticker = item.get("ticker", "")
        price_added = item.get("price_added")
        current = datalib.fetch_last_close(ticker)
        gain = None
        if current is not None and price_added:
            try:
                gain = (current - float(price_added)) / float(price_added) * 100.0
            except (TypeError, ZeroDivisionError):
                gain = None
        position_size = item.get("position_size", 100)
        status = item.get("status", "open")
        sells = item.get("sells", [])
        
        realized_gain = 0.0
        for sell in sells:
            if price_added:
                try:
                    sell_gain = (float(sell["price"]) - float(price_added)) / float(price_added) * 100.0
                    weight = sell.get("percent", 0) / 100.0
                    realized_gain += sell_gain * weight
                except (TypeError, ValueError, ZeroDivisionError):
                    pass

        enriched.append(
            {
                "ticker": ticker,
                "dateAdded": item.get("date_added"),
                "priceAdded": price_added,
                "priceTarget": item.get("price_target"),
                "options": item.get("options", ""),
                "currentPrice": current,
                "verdict": item.get("verdict", "WATCH"),
                "commentary": item.get("commentary", ""),
                "gain": gain,
                "positionSize": position_size,
                "status": status,
                "sells": sells,
                "realizedGain": realized_gain if sells else None,
            }
        )
    enriched.sort(key=lambda x: x.get("dateAdded") or "", reverse=True)
    return enriched
