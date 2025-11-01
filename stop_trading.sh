#!/bin/bash
# 停止交易脚本
# 用法: ./stop_trading.sh

# 设置项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# PID文件路径
PID_FILE="$SCRIPT_DIR/trading.pid"

echo "========================================"
echo "停止AI驱动数字货币自动交易系统"
echo "========================================"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "✗ 未找到运行中的交易系统 (PID文件不存在)"
    echo ""
    echo "如果交易系统确实在运行，请手动查找并停止:"
    echo "  ps aux | grep 'main.py'"
    echo "  kill <PID>"
    exit 1
fi

# 读取PID
TRADING_PID=$(cat "$PID_FILE")

# 检查进程是否存在
if ! ps -p "$TRADING_PID" > /dev/null 2>&1; then
    echo "✗ 进程 $TRADING_PID 未运行"
    echo "正在清理PID文件..."
    rm -f "$PID_FILE"
    exit 0
fi

echo "找到交易系统进程 (PID: $TRADING_PID)"
echo "正在发送停止信号..."

# 发送SIGTERM信号（优雅停止）
kill -TERM "$TRADING_PID" 2>/dev/null

# 等待进程结束（最多15秒）
WAIT_COUNT=0
while ps -p "$TRADING_PID" > /dev/null 2>&1 && [ $WAIT_COUNT -lt 15 ]; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo -n "."
done
echo ""

# 检查进程是否已停止
if ps -p "$TRADING_PID" > /dev/null 2>&1; then
    echo "警告: 进程未响应SIGTERM，发送SIGKILL强制停止..."
    kill -9 "$TRADING_PID" 2>/dev/null
    sleep 1
    
    if ps -p "$TRADING_PID" > /dev/null 2>&1; then
        echo "✗ 无法停止进程 $TRADING_PID"
        echo "请手动停止: kill -9 $TRADING_PID"
        exit 1
    fi
fi

# 清理PID文件
rm -f "$PID_FILE"

echo "✓ 交易系统已成功停止"
echo ""
