import sys
import subprocess
import platform
import os
import shutil

# --- 🔒 ChatApp Flawless Launcher (Universal Python) ---

IS_TERMUX = os.environ.get("TERMUX_VERSION") or os.path.exists("/data/data/com.termux")
VENV_DIR = ".venv"

def setup_termux():
    print("📱 Detected Android (Termux)")
    try:
        import cryptography
        has_crypto = True
    except ImportError:
        has_crypto = False
        
    has_api = shutil.which("termux-bluetooth-scan") is not None
    
    if not has_crypto or not has_api:
        print("📦 Installing Android system dependencies (pkg)...")
        subprocess.run("pkg update -y && pkg install -y python-cryptography termux-api", shell=True)

def ensure_venv():
    if IS_TERMUX: return sys.executable
    
    # Check if already in venv
    if hasattr(sys, 'real_prefix') or (sys.base_prefix != sys.prefix):
        return sys.executable
        
    venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe") if platform.system() == "Windows" else os.path.join(VENV_DIR, "bin", "python3")
    
    if not os.path.exists(venv_python):
        print("🛠️ Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])
        
    return venv_python

def check_deps(py_exec):
    print("📦 Checking Python dependencies...")
    try:
        import rich, prompt_toolkit, cryptography, psutil
        # If all imports work, we still might want to check for updates or missing libs
    except ImportError:
        print("📥 Installing missing Python libraries...")
        try:
            subprocess.check_call([py_exec, "-m", "pip", "install", "rich", "prompt_toolkit", "cryptography", "psutil"])
        except Exception as e:
            print(f"⚠️ Warning: Could not auto-install dependencies: {e}")

    print("🔍 Checking system dependencies...")
    missing_bins = []
    for b in ["ffmpeg", "ffplay"]:
        if not shutil.which(b):
            missing_bins.append(b)
    
    if missing_bins:
        print(f"⚠️  Note: Some voice features may not work because {', '.join(missing_bins)} are missing.")
        if platform.system() == "Windows":
             print("👉 Tip: Install FFmpeg via 'winget install ffmpeg' or from ffmpeg.org")
        elif platform.system() == "Linux":
             print("👉 Tip: Install via 'sudo apt install ffmpeg' or your package manager.")

def main():
    if IS_TERMUX:
        setup_termux()
        py_exec = sys.executable
    else:
        py_exec = ensure_venv()
        
    check_deps(py_exec)
    
    # If we just switched to a venv, re-run with current args
    if py_exec != sys.executable:
        print("🚀 Switching to environment and starting...")
        subprocess.run([py_exec, "chat.py"] + sys.argv[1:])
        sys.exit(0)
    print("🚀 Starting ChatApp...")
    
    cmd = [sys.executable, "chat.py"] + sys.argv[1:]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
