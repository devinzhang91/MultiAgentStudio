#!/bin/bash
#
# OpenClaw TUI Studio 停止脚本
# 功能：根据 PID 文件停止程序
#

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.openclaw.pid"
LOG_FILE="$SCRIPT_DIR/.openclaw.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 显示信息
cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦞 OpenClaw TUI Studio - 停止程序                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

EOF

# 检查 PID 文件是否存在
if [ ! -f "$PID_FILE" ]; then
    print_warning "PID 文件不存在: $PID_FILE"
    print_info "程序可能未运行，或已被手动停止"
    
    # 尝试查找可能残留的进程
    PIDS=$(pgrep -f "openclaw_tui" || true)
    if [ -n "$PIDS" ]; then
        echo ""
        print_warning "发现以下相关进程:"
        ps -fp $PIDS 2>/dev/null || true
        echo ""
        read -p "是否强制终止这些进程? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$PIDS" | xargs kill -TERM 2>/dev/null || true
            sleep 1
            echo "$PIDS" | xargs kill -KILL 2>/dev/null || true
            print_success "进程已终止"
        fi
    fi
    exit 0
fi

# 读取 PID
PID=$(cat "$PID_FILE")

# 检查进程是否存在
if ! ps -p "$PID" > /dev/null 2>&1; then
    print_warning "进程不存在 (PID: $PID)"
    print_info "清理 PID 文件..."
    rm -f "$PID_FILE"
    print_success "已清理"
    exit 0
fi

# 获取进程信息
PROCESS_INFO=$(ps -fp "$PID" 2>/dev/null | grep -v PID || true)
if [ -z "$PROCESS_INFO" ]; then
    print_warning "无法获取进程信息 (PID: $PID)"
else
    print_info "发现运行中的进程:"
    echo "$PROCESS_INFO"
fi
echo ""

# 尝试优雅停止
print_info "尝试优雅停止进程 (PID: $PID)..."
kill -TERM "$PID" 2>/dev/null || true

# 等待进程结束
WAIT_TIME=0
MAX_WAIT=10

while ps -p "$PID" > /dev/null 2>&1 && [ $WAIT_TIME -lt $MAX_WAIT ]; do
    sleep 1
    WAIT_TIME=$((WAIT_TIME + 1))
    echo -ne "${BLUE}[INFO]${NC} 等待进程结束... ($WAIT_TIME/$MAX_WAIT)\r"
done
echo ""

# 检查是否还在运行
if ps -p "$PID" > /dev/null 2>&1; then
    print_warning "进程未响应，强制终止..."
    kill -KILL "$PID" 2>/dev/null || true
    sleep 1
    
    if ps -p "$PID" > /dev/null 2>&1; then
        print_error "无法终止进程 (PID: $PID)，请手动检查"
        exit 1
    else
        print_success "进程已强制终止"
    fi
else
    print_success "进程已正常停止"
fi

# 清理 PID 文件
rm -f "$PID_FILE"
print_info "已清理 PID 文件"

# 显示日志信息
if [ -f "$LOG_FILE" ]; then
    echo ""
    print_info "日志文件: $LOG_FILE"
    print_info "查看最后 10 行日志:"
    tail -n 10 "$LOG_FILE" 2>/dev/null || true
fi

echo ""
print_success "OpenClaw TUI Studio 已停止"
