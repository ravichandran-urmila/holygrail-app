#!/bin/bash
# Run the Holygrail backend (FastAPI) and frontend (Vite) together for local dev.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() { kill 0 2>/dev/null; }
trap cleanup EXIT

echo "→ Starting FastAPI backend on :8000"
(
  cd "$ROOT/backend"
  [ -d .venv ] || python3 -m venv .venv
  source .venv/bin/activate
  pip install -q -r requirements.txt
  uvicorn app.main:app --reload --port 8000
) &

echo "→ Starting Vite frontend on :5173"
(
  cd "$ROOT/frontend"
  [ -d node_modules ] || npm install --cache "$ROOT/frontend/.npm_cache"
  npm run dev
) &

wait
