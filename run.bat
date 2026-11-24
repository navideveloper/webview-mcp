@echo off
setlocal

where uv >nul 2>&1

if %errorlevel% neq 0 (
    echo [INFO] uv not found. Installing uv...

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "irm https://astral.sh/uv/install.ps1 | iex"

    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install uv.
        exit /b 1
    )

    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

echo [INFO] Starting MCP server...

uv run server.py --show True