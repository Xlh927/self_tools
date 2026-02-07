#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "Installing dependencies..."
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements.txt"

if [ "${SKIP_FRONTEND_BUILD:-0}" != "1" ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found. Please install Node.js 18+ for frontend build."
    exit 1
  fi

  echo "Installing frontend dependencies..."
  if [ -f "$FRONTEND_DIR/package-lock.json" ]; then
    npm --prefix "$FRONTEND_DIR" ci
  else
    npm --prefix "$FRONTEND_DIR" install
  fi

  echo "Building frontend bundle with Vite..."
  npm --prefix "$FRONTEND_DIR" run build
fi

echo "Bootstrap completed."
echo "Activate with: source .venv/bin/activate"
