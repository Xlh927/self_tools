#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

"$ROOT_DIR/scripts/bootstrap_dev.sh"

echo "[1/2] Running smoke test..."
"$PYTHON_BIN" "$ROOT_DIR/tests/smoke_test.py"

echo "[2/2] Running core API test..."
"$PYTHON_BIN" "$ROOT_DIR/tests/api_core_test.py"

echo "All checks passed."
