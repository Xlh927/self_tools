#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
DIST_ENTRY="$ROOT_DIR/frontend/dist/cv-tools.html"

BACKEND_PORT="${SELF_TOOLS_BACKEND_PORT:-8080}"
FRONTEND_PORT="${SELF_TOOLS_FRONTEND_PORT:-8081}"
BACKEND_HOST="${SELF_TOOLS_BACKEND_HOST:-0.0.0.0}"
FRONTEND_HOST="${SELF_TOOLS_FRONTEND_HOST:-0.0.0.0}"
BACKEND_PID=""
FRONTEND_PID=""

print_usage() {
  cat <<'EOF'
Usage: ./scripts/run_up.sh [options]

Options:
  --backend-port <port>   Backend port (default: 8080)
  --backend-host <host>   Backend bind host (default: 0.0.0.0)
  --frontend-port <port>  Frontend port (default: 8081)
  --frontend-host <host>  Frontend bind host (default: 0.0.0.0)
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

detect_lan_ips() {
  "$PYTHON_BIN" - <<'PY'
import socket

ips = set()

try:
    hostname = socket.gethostname()
    for result in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM):
        ip = result[4][0]
        if not ip.startswith("127."):
            ips.add(ip)
except Exception:
    pass

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))
    ip = sock.getsockname()[0]
    sock.close()
    if not ip.startswith("127."):
        ips.add(ip)
except Exception:
    pass

for ip in sorted(ips):
    print(ip)
PY
}

print_access_urls() {
  echo "Servers started."
  echo "Local access:"
  echo "  Home    : http://localhost:$FRONTEND_PORT"
  echo "  CV Tools: http://localhost:$FRONTEND_PORT/cv-tools"
  echo "  Viewer  : http://localhost:$FRONTEND_PORT/image-viewer"
  echo "  API Base: http://127.0.0.1:$BACKEND_PORT/api"

  local frontend_is_shared=0
  local backend_is_shared=0
  if [ "$FRONTEND_HOST" = "0.0.0.0" ] || [ "$FRONTEND_HOST" = "::" ] || [ -z "$FRONTEND_HOST" ]; then
    frontend_is_shared=1
  fi
  if [ "$BACKEND_HOST" = "0.0.0.0" ] || [ "$BACKEND_HOST" = "::" ] || [ -z "$BACKEND_HOST" ]; then
    backend_is_shared=1
  fi

  if [ "$frontend_is_shared" = "1" ] || [ "$backend_is_shared" = "1" ]; then
    local lan_ips
    lan_ips="$(detect_lan_ips)"
    if [ -n "$lan_ips" ]; then
      echo "LAN share URLs:"
      while IFS= read -r ip; do
        [ -n "$ip" ] || continue
        if [ "$frontend_is_shared" = "1" ]; then
          echo "  Frontend: http://$ip:$FRONTEND_PORT/cv-tools"
        fi
        if [ "$backend_is_shared" = "1" ]; then
          echo "  API Base: http://$ip:$BACKEND_PORT/api"
        fi
      done <<< "$lan_ips"
    else
      echo "LAN share URLs: unable to auto-detect a non-loopback IPv4 address."
    fi
  else
    echo "LAN sharing is disabled for both frontend and backend."
    echo "Use --frontend-host or --backend-host to expose them."
  fi

  if [ "$frontend_is_shared" = "0" ] && [ -n "$FRONTEND_HOST" ]; then
    echo "Frontend is limited to bind host: $FRONTEND_HOST"
    echo "  http://$FRONTEND_HOST:$FRONTEND_PORT/cv-tools"
  fi
  if [ "$backend_is_shared" = "0" ] && [ -n "$BACKEND_HOST" ]; then
    echo "Backend API is limited to bind host: $BACKEND_HOST"
    echo "  http://$BACKEND_HOST:$BACKEND_PORT/api"
  fi

  echo "Press Ctrl+C to stop."
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --backend-port)
      shift
      [ "$#" -gt 0 ] || { echo "Missing value for --backend-port"; exit 1; }
      BACKEND_PORT="$1"
      ;;
    --backend-host)
      shift
      [ "$#" -gt 0 ] || { echo "Missing value for --backend-host"; exit 1; }
      BACKEND_HOST="$1"
      ;;
    --frontend-port)
      shift
      [ "$#" -gt 0 ] || { echo "Missing value for --frontend-port"; exit 1; }
      FRONTEND_PORT="$1"
      ;;
    --frontend-host)
      shift
      [ "$#" -gt 0 ] || { echo "Missing value for --frontend-host"; exit 1; }
      FRONTEND_HOST="$1"
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
  echo "Try: ./start.sh --backend-port 8080 --frontend-port 8081"
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
  echo "Backend port $BACKEND_PORT is occupied by $(print_port_owner "$BACKEND_PORT")."
  echo "Use another port, for example:"
  echo "  ./start.sh --backend-port 8082 --frontend-port $FRONTEND_PORT"
  exit 1
fi

if port_in_use "$FRONTEND_PORT"; then
  echo "Frontend port $FRONTEND_PORT is occupied by $(print_port_owner "$FRONTEND_PORT")."
  echo "Use another port, for example:"
  echo "  ./start.sh --backend-port $BACKEND_PORT --frontend-port 8082"
  exit 1
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

echo "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
SELF_TOOLS_BACKEND_HOST="$BACKEND_HOST" SELF_TOOLS_BACKEND_PORT="$BACKEND_PORT" "$PYTHON_BIN" "$ROOT_DIR/backend/app.py" &
BACKEND_PID=$!

if ! wait_for_backend_ready; then
  exit 1
fi

echo "Starting frontend shared server on http://$FRONTEND_HOST:$FRONTEND_PORT"
SELF_TOOLS_BACKEND_PORT="$BACKEND_PORT" SELF_TOOLS_FRONTEND_HOST="$FRONTEND_HOST" "$PYTHON_BIN" "$ROOT_DIR/dev_server.py" "$FRONTEND_PORT" &
FRONTEND_PID=$!

print_access_urls

wait
