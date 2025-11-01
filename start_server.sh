#!/usr/bin/env bash
set -euo pipefail

# 进入脚本所在目录（项目根）
cd "$(dirname "$0")"

# 创建日志目录
mkdir -p logs

LOG_FILE="logs/server_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="server.pid"

# 如果已有在运行的服务，提示并退出
if [[ -f "$PID_FILE" ]] && ps -p "$(cat "$PID_FILE" 2>/dev/null)" > /dev/null 2>&1; then
  echo "Server already running with PID $(cat "$PID_FILE"). Stop it first: ./stop_server.sh"
  exit 1
fi

# 使用 nohup 启动，开启无缓冲输出，记录日志
export PYTHONUNBUFFERED=1
nohup python3 -u server.py > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

echo $SERVER_PID > "$PID_FILE"
echo "Server started. PID=$SERVER_PID"
echo "Logs: $LOG_FILE"

echo "Tip: tail -f $LOG_FILE"
