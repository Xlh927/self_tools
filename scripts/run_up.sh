#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
DIST_ENTRY="$ROOT_DIR/frontend/dist/cv-tools.html"

BACKEND_PORT="${SELF_TOOLS_BACKEND_PORT:-5000}"
FRONTEND_PORT="${SELF_TOOLS_FRONTEND_PORT:-8080}"
AUTO_PORT="${SELF_TOOLS_AUTO_PORT:-1}"
BACKEND_PID=""
FRONTEND_PID=""

print_usage() {
  cat <<'EOF'
Usage: ./scripts/run_up.sh [options]

Options:
  --backend-port <port>   Backend port (default: 5000)
  --frontend-port <port>  Frontend port (default: 8080)
  --auto-port             Auto-find next available port when conflict occurs (default)
  --no-auto-port          Fail on port conflict instead of auto-switching
  -h, --help              Show this help
EOF
}

is_valid_port() {
  local port="$1"
  [[ "$port" =~ ^[0-9]+$ ]] && [ "$port" -ge 1 ] && [ "$port" -le 65535 ]
}

port_in_use() {
  local port="$1"
  "$PYTHON_BIN" - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.2)
result = sock.connect_ex(("127.0.0.1", port))
sock.close()
sys.exit(0 if result == 0 else 1)
PY
}

find_next_free_port() {
  local start="$1"
  local port="$start"
  local limit=$((start + 200))
  while [ "$port" -le "$limit" ]; do
    if ! port_in_use "$port"; then
      echo "$port"
      return 0
    fi
    port=$((port + 1))
  done
  return 1
}

wait_for_backend_ready() {
  local retries=60
  while [ "$retries" -gt 0 ]; do
    if [ -n "$BACKEND_PID" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo "Backend process exited before becoming ready."
      return 1
    fi
    if port_in_use "$BACKEND_PORT"; then
      return 0
    fi
    sleep 0.2
    retries=$((retries - 1))
  done
  echo "Backend did not become ready on port $BACKEND_PORT within timeout."
  return 1
}

print_port_owner() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local owner
    owner="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {print $1 " (pid " $2 ")"}')"
    if [ -n "$owner" ]; then
      echo "$owner"
      return
    fi
  fi
  echo "unknown process"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --backend-port)
      shift
      [ "$#" -gt 0 ] || { echo "Missing value for --backend-port"; exit 1; }
      BACKEND_PORT="$1"
      ;;
    --frontend-port)
      shift
      [ "$#" -gt 0 ] || { echo "Missing value for --frontend-port"; exit 1; }
      FRONTEND_PORT="$1"
      ;;
    --auto-port)
      AUTO_PORT=1
      ;;
    --no-auto-port)
      AUTO_PORT=0
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      print_usage
      exit 1
      ;;
  esac
  shift
done

if ! is_valid_port "$BACKEND_PORT"; then
  echo "Invalid backend port: $BACKEND_PORT"
  exit 1
fi
if ! is_valid_port "$FRONTEND_PORT"; then
  echo "Invalid frontend port: $FRONTEND_PORT"
  exit 1
fi
if [ "$BACKEND_PORT" = "$FRONTEND_PORT" ]; then
  echo "Backend and frontend ports must be different."
  echo "Try: ./start.sh --backend-port 5000 --frontend-port 8080"
  exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Virtual environment not found: $PYTHON_BIN"
  echo "Run one-time bootstrap first:"
  echo "  ./scripts/bootstrap_dev.sh"
  exit 1
fi

if [ ! -f "$DIST_ENTRY" ]; then
  echo "Frontend bundle missing: $DIST_ENTRY"
  echo "Run one-time bootstrap first:"
  echo "  ./scripts/bootstrap_dev.sh"
  exit 1
fi

if port_in_use "$BACKEND_PORT"; then
  if [ "$AUTO_PORT" = "1" ]; then
    next_port="$(find_next_free_port "$BACKEND_PORT")" || {
      echo "No available backend port found near $BACKEND_PORT"
      exit 1
    }
    echo "Backend port $BACKEND_PORT is occupied by $(print_port_owner "$BACKEND_PORT")."
    echo "Auto-selected backend port: $next_port"
    BACKEND_PORT="$next_port"
  else
    echo "Backend port $BACKEND_PORT is occupied by $(print_port_owner "$BACKEND_PORT")."
    echo "Use another port, for example:"
    echo "  ./start.sh --backend-port 5001 --frontend-port $FRONTEND_PORT"
    echo "Or auto-select ports:"
    echo "  ./start.sh --auto-port"
    exit 1
  fi
fi

if port_in_use "$FRONTEND_PORT"; then
  if [ "$AUTO_PORT" = "1" ]; then
    next_port="$(find_next_free_port "$FRONTEND_PORT")" || {
      echo "No available frontend port found near $FRONTEND_PORT"
      exit 1
    }
    echo "Frontend port $FRONTEND_PORT is occupied by $(print_port_owner "$FRONTEND_PORT")."
    echo "Auto-selected frontend port: $next_port"
    FRONTEND_PORT="$next_port"
  else
    echo "Frontend port $FRONTEND_PORT is occupied by $(print_port_owner "$FRONTEND_PORT")."
    echo "Use another port, for example:"
    echo "  ./start.sh --backend-port $BACKEND_PORT --frontend-port 8081"
    echo "Or auto-select ports:"
    echo "  ./start.sh --auto-port"
    exit 1
  fi
fi

# Auto-port mode could pick equal values after conflict handling.
if [ "$BACKEND_PORT" = "$FRONTEND_PORT" ]; then
  if [ "$AUTO_PORT" = "1" ]; then
    next_port="$(find_next_free_port "$FRONTEND_PORT")" || {
      echo "No available frontend port found near $FRONTEND_PORT"
      exit 1
    }
    FRONTEND_PORT="$next_port"
  else
    echo "Backend and frontend ports conflict after resolution."
    exit 1
  fi
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

echo "Starting backend on http://127.0.0.1:$BACKEND_PORT"
SELF_TOOLS_BACKEND_PORT="$BACKEND_PORT" "$PYTHON_BIN" "$ROOT_DIR/backend/app.py" &
BACKEND_PID=$!

if ! wait_for_backend_ready; then
  exit 1
fi

echo "Starting frontend dev server on http://localhost:$FRONTEND_PORT"
SELF_TOOLS_BACKEND_PORT="$BACKEND_PORT" "$PYTHON_BIN" "$ROOT_DIR/dev_server.py" "$FRONTEND_PORT" &
FRONTEND_PID=$!

echo "Servers started."
echo "  Home: http://localhost:$FRONTEND_PORT"
echo "  API : http://127.0.0.1:$BACKEND_PORT"
echo "Press Ctrl+C to stop."

wait
