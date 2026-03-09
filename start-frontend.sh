#!/bin/bash
#
# 启动 TUI 前端
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$FRONTEND_DIR/.venv"

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}[INFO]${NC} 启动 OpenClaw Frontend (TUI)..."

# 检查后端是否运行
if ! curl -s http://localhost:18765 > /dev/null 2>&1; then
    echo -e "${BLUE}[INFO]${NC} 后端服务未启动，请先运行 ./start-backend.sh"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "创建前端虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

# 激活并安装
source "$VENV_DIR/bin/activate"
pip install -q --upgrade pip
pip install -q -e "$FRONTEND_DIR"

# 启动前端（前台运行，占用终端）
echo ""
python3 -m openclaw_frontend
