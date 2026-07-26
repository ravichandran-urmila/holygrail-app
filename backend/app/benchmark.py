import json
import os
import time
import requests
from pathlib import Path

_GH_API = "https://api.github.com"
_EVAL_PATH = Path(os.path.dirname(__file__)) / "eval_dataset.json"
_ACTIVE_PATH = Path(os.path.dirname(__file__)) / "active_model.json"

# Candidate open-source models to benchmark
CANDIDATES = [
    "moonshotai/Kimi-K2-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "Qwen/Qwen2.5-1.5B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
    "google/gemma-3-1b-it"
]

def _gh_cfg():
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPO", "")
    branch = os.environ.get("GITHUB_BRANCH", "master")
    path = "backend/app/active_model.json"
    if token and repo:
        return token, repo, branch, path
    return None

def load_active_model() -> str:
    # Load from local cache / GitHub
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
                import base64
                raw = base64.b64decode(r.json()["content"]).decode("utf-8")
                return json.loads(raw).get("model", CANDIDATES[0])
        except Exception:
            pass

    if _ACTIVE_PATH.exists():
        try:
            with open(_ACTIVE_PATH, "r") as f:
                return json.load(f).get("model", CANDIDATES[0])
        except Exception:
            pass
    return CANDIDATES[0]

def save_active_model(model_name: str) -> bool:
    payload_str = json.dumps({"model": model_name, "updated_at": time.time()}, indent=2)
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
                "message": f"chore: update active LLM model to {model_name}",
                "content": requests.utils.base64.b64encode(payload_str.encode()).decode(),
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
        except Exception:
            pass

    try:
        with open(_ACTIVE_PATH, "w") as f:
            f.write(payload_str)
        return True
    except Exception:
        return False

def calculate_jaccard_similarity(str1: str, str2: str) -> float:
    # Zero-dependency token similarity scoring
    words1 = set(str1.lower().replace(",", "").replace(".", "").split())
    words2 = set(str2.lower().replace(",", "").replace(".", "").split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

def evaluate_model(model_name: str, hf_token: str, dataset: list) -> dict:
    valid_count = 0
    total_similarity = 0.0
    total_latency = 0.0
    errors = 0

    for item in dataset:
        prompt = f"""Extract financial entities from the following news article. Output ONLY a valid JSON object matching this schema:
{{
  "company": "string",
  "catalyst": "string",
  "sentiment": "bullish" | "bearish"
}}

Article: "{item['article_text']}"
"""
        start_time = time.time()
        try:
            resp = requests.post(
                "https://router.huggingface.co/v1/chat/completions",
                headers={"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"},
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.1,
                },
                timeout=10,
            )
            latency = time.time() - start_time
            total_latency += latency

            if resp.status_code == 200:
                raw_out = resp.json()["choices"][0]["message"]["content"].strip()
                # Clean code blocks if present
                if raw_out.startswith("```"):
                    raw_out = raw_out.strip("`").replace("json\n", "").strip()
                
                parsed = json.loads(raw_out)
                if all(k in parsed for k in ("company", "catalyst", "sentiment")):
                    valid_count += 1
                    sim = calculate_jaccard_similarity(parsed["catalyst"], item["gold_output"]["catalyst"])
                    total_similarity += sim
            else:
                import logging
                logging.getLogger("uvicorn.error").warning(f"Benchmark model {model_name} failed with status {resp.status_code}: {resp.text[:100]}")
                errors += 1
        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").error(f"Benchmark model {model_name} exception: {str(e)}")
            errors += 1

    total_items = len(dataset)
    json_pass_rate = valid_count / total_items
    avg_similarity = total_similarity / max(1, valid_count)
    avg_latency = total_latency / total_items

    # Latency penalty: 1.0 for <=3s, down to 0.0 for >=10s
    latency_score = max(0.0, 1.0 - (max(0.0, avg_latency - 3.0) / 7.0))

    # Overall weighted score
    overall_score = (json_pass_rate * 0.4) + (avg_similarity * 0.5) + (latency_score * 0.1)

    return {
        "model": model_name,
        "overall_score": overall_score,
        "json_pass_rate": json_pass_rate,
        "avg_similarity": avg_similarity,
        "avg_latency": avg_latency,
        "errors": errors
    }

def run_weekly_benchmark() -> dict:
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    if not hf_token:
        return {"status": "error", "message": "HF_TOKEN env variable not set"}

    if not _EVAL_PATH.exists():
        return {"status": "error", "message": "Evaluation dataset missing"}

    with open(_EVAL_PATH, "r") as f:
        dataset = json.load(f)

    results = []
    best_model = None
    best_score = -1.0

    for model in CANDIDATES:
        res = evaluate_model(model, hf_token, dataset)
        results.append(res)
        if res["overall_score"] > best_score and res["errors"] < (len(dataset) / 2):
            best_score = res["overall_score"]
            best_model = model

    current_active = load_active_model()
    swapped = False

    if best_model and best_model != current_active:
        save_active_model(best_model)
        swapped = True

    return {
        "status": "success",
        "active_model": best_model or current_active,
        "previous_model": current_active,
        "swapped": swapped,
        "leaderboard": sorted(results, key=lambda x: x["overall_score"], reverse=True)
    }
