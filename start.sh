#!/bin/bash
#
# OpenClaw TUI Studio 启动脚本
# 功能：创建虚拟环境、安装依赖、启动程序、记录pid、记录log
#

set -e  # 遇到错误立即退出

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PID_FILE="$SCRIPT_DIR/.openclaw.pid"
LOG_FILE="$SCRIPT_DIR/.openclaw.log"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示欢迎信息
cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦞 OpenClaw TUI Studio - 可视化 OpenClaw 工作室         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

EOF

# 检查 Python 版本
print_info "检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    print_error "未找到 python3，请先安装 Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python 版本需要 >= 3.9，当前版本: $PYTHON_VERSION"
    exit 1
fi
print_success "Python 版本: $PYTHON_VERSION"

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        print_warning "程序已经在运行 (PID: $PID)"
        print_info "使用 ./stop.sh 停止程序，或使用 ./stop.sh && ./start.sh 重启"
        exit 1
    else
        print_warning "发现过期的 PID 文件，清理中..."
        rm -f "$PID_FILE"
    fi
fi

# 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    print_info "创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
    print_success "虚拟环境创建完成: $VENV_DIR"
else
    print_info "虚拟环境已存在: $VENV_DIR"
fi

# 激活虚拟环境
print_info "激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 升级 pip
print_info "升级 pip..."
pip install --upgrade pip -q

# 安装依赖
if [ -f "$REQUIREMENTS" ]; then
    print_info "安装依赖..."
    pip install -r "$REQUIREMENTS" -q
    print_success "依赖安装完成"
else
    print_warning "未找到 requirements.txt，跳过依赖安装"
fi

# 清理旧日志
if [ -f "$LOG_FILE" ]; then
    print_info "备份旧日志..."
    mv "$LOG_FILE" "${LOG_FILE}.old"
fi

# 启动程序
print_info "启动 OpenClaw TUI Studio..."
print_info "日志文件: $LOG_FILE"
print_info "PID 文件: $PID_FILE"
echo ""

# 启动程序并记录 PID
python3 -m openclaw_tui "$@" &
PID=$!
echo $PID > "$PID_FILE"

# 等待程序启动
sleep 1

if ps -p "$PID" > /dev/null 2>&1; then
    print_success "程序已启动 (PID: $PID)"
    echo ""
    print_info "提示:"
    echo "  - 查看日志: tail -f $LOG_FILE"
    echo "  - 停止程序: ./stop.sh"
    echo "  - 程序正在运行，请查看终端窗口"
    echo ""
    
    # 将输出重定向到日志文件
    exec &> >(tee -a "$LOG_FILE")
    
    # 等待进程结束
    wait $PID
    EXIT_CODE=$?
    
    # 清理 PID 文件
    rm -f "$PID_FILE"
    
    if [ $EXIT_CODE -ne 0 ]; then
        print_error "程序异常退出 (退出码: $EXIT_CODE)"
        print_info "查看日志: tail -n 50 $LOG_FILE"
        exit $EXIT_CODE
    fi
else
    print_error "程序启动失败"
    rm -f "$PID_FILE"
    exit 1
fi
