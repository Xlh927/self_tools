#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
FRONTEND_DIR="$ROOT_DIR/frontend"
DIST_ENTRY="$FRONTEND_DIR/dist/cv-tools.html"
WHEELHOUSE_DIR="$ROOT_DIR/wheelhouse"

is_supported_python() {
  local version="$1"
  if [ -z "$version" ]; then
    return 1
  fi

  local major="${version%%.*}"
  local minor="${version#*.}"
  if [ "$major" != "3" ]; then
    return 1
  fi
  if [ "$minor" -lt 9 ] || [ "$minor" -gt 12 ]; then
    return 1
  fi
  return 0
}

resolve_python() {
  local candidates=()
  if [ -n "${SELF_TOOLS_PYTHON:-}" ]; then
    candidates+=("${SELF_TOOLS_PYTHON}")
  fi
  candidates+=(python3.12 python3.11 python3.10 python3.9 /usr/bin/python3 python3)

  local candidate=""
  local version=""
  for candidate in "${candidates[@]}"; do
    if [[ "$candidate" = /* ]]; then
      if [ ! -x "$candidate" ]; then
        continue
      fi
    else
      if ! command -v "$candidate" >/dev/null 2>&1; then
        continue
      fi
    fi

    version="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
    if is_supported_python "$version"; then
      echo "$candidate"
      return 0
    fi
  done

  return 1
}

SELECTED_PYTHON="$(resolve_python || true)"
if [ -z "$SELECTED_PYTHON" ]; then
  echo "No supported Python interpreter found."
  echo "Required Python version: 3.9 - 3.12"
  echo "Current python3: $(python3 --version 2>/dev/null || echo missing)"
  echo "You can set SELF_TOOLS_PYTHON to specify interpreter path."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at $VENV_DIR"
  "$SELECTED_PYTHON" -m venv "$VENV_DIR"
fi

VENV_PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
if ! is_supported_python "$VENV_PY_VERSION"; then
  echo "Existing virtual environment uses unsupported Python $VENV_PY_VERSION."
  echo "Please recreate it with a supported interpreter (3.9 - 3.12):"
  echo "  rm -rf \"$VENV_DIR\""
  echo "  SELF_TOOLS_PYTHON=\"$SELECTED_PYTHON\" ./start.sh"
  exit 1
fi

echo "Installing dependencies..."
if [ "${SELF_TOOLS_OFFLINE_INSTALL:-0}" = "1" ]; then
  if [ ! -d "$WHEELHOUSE_DIR" ]; then
    echo "Offline install requested but wheelhouse is missing: $WHEELHOUSE_DIR"
    echo "Rebuild runtime bundle on a machine with internet access:"
    echo "  ./scripts/build_runtime_bundle.sh"
    exit 1
  fi
  echo "Installing dependencies from local wheelhouse (offline mode)..."
  "$PYTHON_BIN" -m pip install --no-index --find-links "$WHEELHOUSE_DIR" -r "$ROOT_DIR/requirements.txt"
elif [ -d "$WHEELHOUSE_DIR" ]; then
  echo "Installing dependencies from local wheelhouse..."
  if ! "$PYTHON_BIN" -m pip install --no-index --find-links "$WHEELHOUSE_DIR" -r "$ROOT_DIR/requirements.txt"; then
    echo "Local wheelhouse install failed, falling back to online install..."
    "$PYTHON_BIN" -m pip install --upgrade pip
    "$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements.txt"
  fi
else
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements.txt"
fi

if [ "${SKIP_FRONTEND_BUILD:-0}" != "1" ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "Installing frontend dependencies..."
    if [ -f "$FRONTEND_DIR/package-lock.json" ]; then
      npm --prefix "$FRONTEND_DIR" ci
    else
      npm --prefix "$FRONTEND_DIR" install
    fi

    echo "Building frontend bundle with Vite..."
    npm --prefix "$FRONTEND_DIR" run build
  elif [ -f "$DIST_ENTRY" ]; then
    echo "npm not found. Using existing frontend bundle at $DIST_ENTRY"
  else
    echo "Frontend bundle missing: $DIST_ENTRY"
    echo "To run without Node.js, prepare a runtime bundle on a build machine:"
    echo "  ./scripts/build_runtime_bundle.sh"
    echo "Or install Node.js 18+ and build locally:"
    echo "  npm --prefix frontend ci && npm --prefix frontend run build"
    exit 1
  fi
else
  echo "Skipping frontend dependency install/build (SKIP_FRONTEND_BUILD=1)."
fi

echo "Bootstrap completed."
echo "Activate with: source .venv/bin/activate"
