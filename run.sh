#!/bin/bash
# 🦞 MushTech TUI Studio - Run Script

set -e

cd "$(dirname "$0")"

# Check venv
if [ ! -d ".venv" ]; then
    echo "[!] Virtual environment not found. Creating..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Check deps
if ! python3 -c "import textual, aiohttp, cryptography" 2>/dev/null; then
    echo "[!] Installing dependencies..."
    pip install textual aiohttp cryptography
fi

# Run
exec python3 -m mushtech_studio "$@"
