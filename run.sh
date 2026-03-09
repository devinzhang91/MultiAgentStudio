#!/bin/bash
# 🦞 OpenClaw TUI Studio - 启动脚本

cd "$(dirname "$0")"

# 检查依赖
echo "检查依赖..."
python3 -c "import textual, aiohttp, cryptography" 2>/dev/null || {
    echo "安装依赖..."
    pip3 install textual aiohttp cryptography
}

# 运行
echo "启动 OpenClaw Studio..."
python3 openclaw_studio.py
