#!/bin/bash
# 启动持续交易脚本
# 用法: ./start_trading.sh [间隔分钟数，默认3]

# 设置项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# PID文件路径
PID_FILE="$SCRIPT_DIR/trading.pid"

# 日志目录
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# 日志文件（按日期命名）
LOG_FILE="$LOG_DIR/trading_$(date +%Y%m%d_%H%M%S).log"

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "错误: 交易系统已在运行 (PID: $OLD_PID)"
        echo "请先运行 ./stop_trading.sh 停止现有进程"
        exit 1
    else
        echo "发现过期的PID文件，正在清理..."
        rm -f "$PID_FILE"
    fi
fi

# 获取间隔时间参数（默认3分钟）
INTERVAL=${1:-3}

echo "========================================"
echo "启动AI驱动数字货币自动交易系统"
echo "========================================"
echo "运行模式: 持续运行"
echo "执行间隔: ${INTERVAL} 分钟"
echo "日志文件: $LOG_FILE"
echo "PID文件:  $PID_FILE"
echo "========================================"

# 启动主程序（后台运行）
nohup python3 main.py --mode continuous --interval "$INTERVAL" >> "$LOG_FILE" 2>&1 &

# 保存PID
MAIN_PID=$!
echo "$MAIN_PID" > "$PID_FILE"

# 等待片刻确认启动
sleep 2

# 检查进程是否成功启动
if ps -p "$MAIN_PID" > /dev/null 2>&1; then
    echo "✓ 交易系统启动成功 (PID: $MAIN_PID)"
    echo ""
    echo "使用以下命令查看实时日志:"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "使用以下命令停止交易:"
    echo "  ./stop_trading.sh"
    echo ""
else
    echo "✗ 交易系统启动失败"
    echo "请检查日志文件: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
