#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$DIR/.env" ]; then
  set -a && source "$DIR/.env" && set +a
fi

echo "API  → http://localhost:8000"
echo "App  → http://localhost:5173"

# Start FastAPI backend (api/main.py) on port 8000
cd "$DIR"
.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Start Vite frontend on port 5173
cd "$DIR/dashboard"
npm run dev &
VITE_PID=$!

# Cleanup on exit
trap "kill $API_PID $VITE_PID 2>/dev/null" EXIT INT TERM

wait
