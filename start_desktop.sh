#!/bin/bash
set -euo pipefail

PROJECT_DIR="/media/qzq/4t/AAA_myproject/self_tools"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Run in background and capture logs
nohup bash -lc "source /home/qzq/anaconda3/etc/profile.d/conda.sh && conda activate /home/qzq/anaconda3/envs/self_tools && cd '$PROJECT_DIR' && ./start.sh" \
  >"$LOG_DIR/start.log" 2>"$LOG_DIR/start.err" &

# Give servers a moment to boot, then open browser
sleep 2
xdg-open "http://localhost:8080" >/dev/null 2>&1 || true

echo "Started. Logs: $LOG_DIR/start.log / $LOG_DIR/start.err"
