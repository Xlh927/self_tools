#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${SELF_TOOLS_PYTHON:-python3}"

exec "$PYTHON_BIN" "$ROOT_DIR/scripts/build_runtime_bundle.py" "$@"
