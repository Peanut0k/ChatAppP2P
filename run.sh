#!/bin/bash

# --- 🔒 ChatApp Flawless Launcher (Linux/Android) ---

VENV_DIR=".venv"
IS_TERMUX=false
if [ -d "/data/data/com.termux" ]; then IS_TERMUX=true; fi

# 1. Termux Specific Setup
if [ "$IS_TERMUX" = true ]; then
    if ! command -v termux-bluetooth-scan &> /dev/null || ! python3 -c "import cryptography" &> /dev/null; then
        echo "📦 Installing Android system dependencies (pkg)..."
        pkg update -y && pkg install -y python-cryptography termux-api
    fi
    PYTHON_EXEC="python3"
else
    # 2. Linux Venv Setup
    if [ ! -d "$VENV_DIR" ]; then
        echo "🛠️ Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    PYTHON_EXEC="$VENV_DIR/bin/python3"
fi

# 3. Install Python Dependencies
echo "📦 Checking dependencies..."
$PYTHON_EXEC -m pip install rich prompt_toolkit cryptography &> /dev/null

# 4. Launch App
$PYTHON_EXEC chat.py "$@"
