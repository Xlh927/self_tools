#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$ROOT_DIR/.venv/bin/python"
RUNTIME_MARKER="$ROOT_DIR/BUNDLE_INFO.txt"
DIST_ENTRY="$ROOT_DIR/frontend/dist/cv-tools.html"

run_bootstrap() {
  local skip_frontend_build=0
  local offline_install=0

  if [ -f "$RUNTIME_MARKER" ] && grep -q '^node_required_at_runtime=no$' "$RUNTIME_MARKER"; then
    echo "Runtime bundle detected. Skipping frontend build during bootstrap."
    skip_frontend_build=1
    if [ -d "$ROOT_DIR/wheelhouse" ]; then
      echo "Runtime wheelhouse detected. Enabling offline dependency install."
      offline_install=1
    fi
  elif [ -f "$DIST_ENTRY" ]; then
    echo "Prebuilt frontend bundle detected. Skipping frontend build during bootstrap."
    skip_frontend_build=1
  fi

  if [ "$skip_frontend_build" = "1" ] && [ "$offline_install" = "1" ]; then
    SKIP_FRONTEND_BUILD=1 SELF_TOOLS_OFFLINE_INSTALL=1 "$ROOT_DIR/scripts/bootstrap_dev.sh"
  elif [ "$skip_frontend_build" = "1" ]; then
    SKIP_FRONTEND_BUILD=1 "$ROOT_DIR/scripts/bootstrap_dev.sh"
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
