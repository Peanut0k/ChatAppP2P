#!/bin/bash

# ChatApp Launcher Script
# This script handles venv creation, installation, and launching the app.

VENV_DIR=".venv"
PYTHON_BIN="python3"

# 1. Check for Python
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    exit 1
fi

# 2. Create/Activate Virtual Environment
if [ ! -d "$VENV_DIR" ]; then
    echo "🛠️ Creating virtual environment..."
    $PYTHON_BIN -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# 3. Install Dependencies
echo "📦 Checking dependencies..."
pip install -q cryptography rich

# 4. Handle Arguments
case "$1" in
    "server")
        echo "🚀 Starting Server..."
        python3 chat.py server
        ;;
    "client")
        if [ -z "$2" ]; then
            echo "❌ Error: Please provide the server's MAC address."
            echo "Usage: ./run.sh client AA:BB:CC:DD:EE:FF"
            exit 1
        fi
        echo "🚀 Starting Client... connecting to $2"
        python3 chat.py client "$2"
        ;;
    *)
        echo "📖 Usage:"
        echo "  ./run.sh server         - Start waiting for a friend"
        echo "  ./run.sh client <MAC>   - Connect to your friend's MAC address"
        echo ""
        echo "To find your MAC address, run: hciconfig"
        ;;
esac
