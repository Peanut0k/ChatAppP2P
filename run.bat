@echo off
setlocal

:: --- 🔒 ChatApp Flawless Launcher (Windows) ---

set VENV_DIR=.venv

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

:: 2. Venv Setup
if not exist %VENV_DIR% (
    echo 🛠️ Creating virtual environment...
    python -m venv %VENV_DIR%
)
set PYTHON_EXEC=%VENV_DIR%\Scripts\python.exe

:: 3. Install Dependencies
echo 📦 Checking dependencies...
%PYTHON_EXEC% -m pip install --upgrade pip >nul 2>&1
%PYTHON_EXEC% -m pip install rich prompt_toolkit cryptography >nul 2>&1

:: 4. Launch App
echo 🚀 Starting ChatApp...
%PYTHON_EXEC% chat.py %*

if %errorlevel% neq 0 (
    if %errorlevel% neq 130 (
        echo.
        echo ❌ App crashed with error code %errorlevel%
        pause
    )
)
