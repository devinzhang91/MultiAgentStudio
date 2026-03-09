#!/bin/bash
#
# 停止后端服务
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.backend.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "后端服务未运行"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "停止后端服务 (PID: $PID)..."
    kill "$PID"
    sleep 2
    
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "强制终止..."
        kill -9 "$PID"
    fi
    
    echo "已停止"
else
    echo "进程不存在"
fi

rm -f "$PID_FILE"
