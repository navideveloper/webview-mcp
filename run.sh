#!/usr/bin/env bash

set -e

if ! command -v uv >/dev/null 2>&1; then
    echo "[INFO] uv not found. Installing uv..."

    curl -LsSf https://astral.sh/uv/install.sh | sh

    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
if ! python3 -c "import gi; gi.require_version('Gtk', '3.0')" >/dev/null 2>&1; then
    echo "[INFO] GTK not found. Installing GTK dependencies..."
    sudo apt update
    sudo apt install -y python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 libgirepository1.0-dev libcairo2-dev pkg-config
    uv sync
    uv pip install --python .venv/bin/python PyGObject
fi

echo "[INFO] Starting MCP server..."

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
uv run server.py --show True