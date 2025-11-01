#!/bin/zsh
# 实时查看最新交易日志
# 用法: ./tail_trading_logs.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

if [ ! -d "$LOG_DIR" ]; then
  echo "日志目录不存在: $LOG_DIR"
  exit 1
fi

LATEST_LOG=$(ls -t "$LOG_DIR"/trading_*.log 2>/dev/null | head -1)
if [ -z "$LATEST_LOG" ]; then
  echo "未找到日志文件，请先运行 ./start_trading.sh 启动系统"
  exit 1
fi

echo "正在尾随日志: $LATEST_LOG"

tail -f "$LATEST_LOG"
