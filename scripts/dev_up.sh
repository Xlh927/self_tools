#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
BACKEND_PID=""
FRONTEND_PID=""

"$ROOT_DIR/scripts/bootstrap_dev.sh"

if command -v lsof >/dev/null 2>&1; then
  lsof -ti:5000 | xargs kill -9 2>/dev/null || true
  lsof -ti:8080 | xargs kill -9 2>/dev/null || true
fi

cleanup() {
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting backend on http://127.0.0.1:5000"
"$PYTHON_BIN" "$ROOT_DIR/backend/app.py" &
BACKEND_PID=$!

sleep 1

echo "Starting frontend dev server on http://localhost:8080"
"$PYTHON_BIN" "$ROOT_DIR/dev_server.py" 8080 &
FRONTEND_PID=$!

echo "Servers started."
echo "  Home: http://localhost:8080"
echo "  API : http://127.0.0.1:5000"
echo "Press Ctrl+C to stop."

wait
