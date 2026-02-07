#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$ROOT_DIR/.venv/bin/python"
RUNTIME_MARKER="$ROOT_DIR/BUNDLE_INFO.txt"

run_bootstrap() {
  if [ -f "$RUNTIME_MARKER" ] && grep -q '^node_required_at_runtime=no$' "$RUNTIME_MARKER"; then
    echo "Runtime bundle detected. Skipping frontend build during bootstrap."
    if [ -d "$ROOT_DIR/wheelhouse" ]; then
      echo "Runtime wheelhouse detected. Enabling offline dependency install."
      SKIP_FRONTEND_BUILD=1 SELF_TOOLS_OFFLINE_INSTALL=1 "$ROOT_DIR/scripts/bootstrap_dev.sh"
    else
      SKIP_FRONTEND_BUILD=1 "$ROOT_DIR/scripts/bootstrap_dev.sh"
    fi
  else
    "$ROOT_DIR/scripts/bootstrap_dev.sh"
  fi
}

if [ "${1:-}" = "--bootstrap" ]; then
  shift
  run_bootstrap
elif [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  "$ROOT_DIR/scripts/dev_up.sh" "$@"
  exit 0
elif [ ! -x "$VENV_PY" ]; then
  echo "Virtual environment not found. Running one-time bootstrap..."
  run_bootstrap
fi

"$ROOT_DIR/scripts/dev_up.sh" "$@"
