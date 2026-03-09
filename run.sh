#!/bin/bash
# 🦞 OpenClaw TUI Studio - 启动脚本
# 自动创建虚拟环境并安装依赖

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║   🦞 OpenClaw TUI Studio                                  ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 检查 Python 版本
echo -e "${BLUE}[INFO]${NC} 检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}[ERROR]${NC} 未找到 python3，请先安装 Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}[OK]${NC} Python 版本: $PYTHON_VERSION"

# 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BLUE}[INFO]${NC} 创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}[OK]${NC} 虚拟环境创建完成"
fi

# 激活虚拟环境
echo -e "${BLUE}[INFO]${NC} 激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 升级 pip
echo -e "${BLUE}[INFO]${NC} 升级 pip..."
pip install --quiet --upgrade pip

# 检查并安装依赖
echo -e "${BLUE}[INFO]${NC} 检查依赖..."

install_dependency() {
    local package=$1
    local import_name=${2:-$package}
    
    if python3 -c "import $import_name" 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} $package 已安装"
        return 0
    else
        echo -e "${YELLOW}[INSTALL]${NC} 安装 $package..."
        pip install --quiet "$package"
        echo -e "${GREEN}[OK]${NC} $package 安装完成"
        return 0
    fi
}

install_dependency "textual" "textual"
install_dependency "aiohttp" "aiohttp"
install_dependency "cryptography" "cryptography"

echo ""
echo -e "${GREEN}[SUCCESS]${NC} 依赖检查完成！"
echo ""

# 运行程序
echo -e "${BLUE}[INFO]${NC} 启动 OpenClaw Studio..."
echo ""

# 使用虚拟环境的 Python 运行
exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/openclaw_studio.py"
