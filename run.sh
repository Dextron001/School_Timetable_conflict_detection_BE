#!/usr/bin/env bash
# Starts backend + frontend together. Linux / macOS.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "▶ Starting FastAPI backend on :8000 ..."
cd "$ROOT/backend"
uvicorn app.main:app --reload --port 8000 &
BACK=$!

echo "▶ Starting React (Vite) frontend on :5173 ..."
cd "$ROOT/frontend"
npm run dev &
FRONT=$!

trap "echo; echo 'Stopping...'; kill $BACK $FRONT 2>/dev/null" INT TERM
wait
