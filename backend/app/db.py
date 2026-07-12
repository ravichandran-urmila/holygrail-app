import base64
import json
import os
import time
import requests
from pathlib import Path

_GH_API = "https://api.github.com"
_LOCAL_PATH = Path(os.path.dirname(__file__)) / ".." / "screener_cache.json"

def _gh_cfg():
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPO", "")
    branch = os.environ.get("GITHUB_BRANCH", "master")
    path = "screener_cache.json"
    if token and repo:
        return token, repo, branch, path
    return None

_cache: dict = {}
_cache_time: float = 0.0

def init_db():
    pass

def _load_all() -> dict:
    global _cache, _cache_time
    now = time.time()
    if _cache and (now - _cache_time < 10.0):
        return _cache

    data = {}
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
                _cache = data
                _cache_time = now
                return data
        except Exception:
            pass

    if _LOCAL_PATH.exists():
        try:
            with open(_LOCAL_PATH, "r") as f:
                data = json.load(f)
                _cache = data
                _cache_time = now
                return data
        except Exception:
            pass
    return data

def _save_all(data: dict) -> bool:
    payload_str = json.dumps(data, indent=2)
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
                "message": "chore: update screener cache",
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
            if r_put.status_code in (200, 201):
                return True
            else:
                print(f"GitHub API Error: {r_put.status_code} {r_put.text}")
                return False
        except Exception as e:
            print(f"GitHub Sync Exception: {str(e)}")
            return False

    try:
        with open(_LOCAL_PATH, "w") as f:
            f.write(payload_str)
        return True
    except Exception:
        return False

def save_cache(universe: str, results: list, state: str, total: int, done: int):
    global _cache, _cache_time
    all_data = _load_all()
    all_data[universe] = {
        "universe": universe,
        "results": results,
        "updated_at": time.time(),
        "total_tickers": total,
        "done_tickers": done,
        "state": state,
    }
    _save_all(all_data)
    _cache = all_data
    _cache_time = time.time()

def load_cache(universe: str) -> dict | None:
    all_data = _load_all()
    return all_data.get(universe)
