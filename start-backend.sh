#!/bin/bash
#
# 启动后端服务（后台守护进程）
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
PID_FILE="$SCRIPT_DIR/.backend.pid"
LOG_FILE="$SCRIPT_DIR/.backend.log"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}[INFO]${NC} 启动 OpenClaw Backend..."

# 检查是否已在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}[WARN]${NC} 后端服务已在运行 (PID: $PID)"
        echo "使用 ./stop-backend.sh 停止"
        exit 1
    fi
fi

# 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "创建后端虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

# 激活并安装
source "$VENV_DIR/bin/activate"
pip install -q --upgrade pip
pip install -q -e "$BACKEND_DIR"

# 启动后端（后台运行）
nohup python3 -m openclaw_backend.server > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"

sleep 2

if ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${GREEN}[SUCCESS]${NC} 后端服务已启动"
    echo "  PID: $PID"
    echo "  日志: $LOG_FILE"
    echo "  API: http://localhost:18765"
    echo ""
    echo "使用 ./start-frontend.sh 启动 TUI 前端"
else
    echo "启动失败，查看日志: $LOG_FILE"
    exit 1
fi
