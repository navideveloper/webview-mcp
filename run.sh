#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v uv >/dev/null 2>&1; then
    echo "[INFO] Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

echo "[INFO] Installing GTK dependencies..."

sudo apt update
sudo apt install -y \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-webkit2-4.1 \
    libcairo2-dev \
    pkg-config

echo "[INFO] Setting up Python environment..."

if [ ! -d ".venv" ]; then
    uv venv --system-site-packages --python /usr/bin/python3
fi

uv sync

echo "[INFO] Starting MCP server..."

uv run server.py --show True