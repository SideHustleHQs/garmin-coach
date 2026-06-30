#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Activeer venv
source .venv/bin/activate

# Ingest meest recente data
echo "=== Ingest ==="
python ingest.py --athlete vriendin --name "Vriendin"

# Start API in background
echo "=== API starten op :8000 ==="
uvicorn api.main:app --port 8000 &
API_PID=$!

# Wacht tot API up is
for i in $(seq 1 20); do
  curl -s http://localhost:8000/api/athletes >/dev/null 2>&1 && break
  sleep 0.3
done

# Start dashboard
echo "=== Dashboard starten op :5173 ==="
cd dashboard
npm run dev &
DASH_PID=$!

echo ""
echo "✓ Dashboard: http://localhost:5173"
echo "✓ API:       http://localhost:8000"
echo ""
echo "Ctrl-C om te stoppen."

cleanup() {
  kill "$API_PID" "$DASH_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM
wait
