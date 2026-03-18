import sys
import subprocess
import platform
import os
import shutil

# On Termux, we usually want to use global packages from 'pkg'
IS_TERMUX = os.environ.get("TERMUX_VERSION") or os.path.exists("/data/data/com.termux")
VENV_DIR = ".venv"

def ensure_venv():
    if IS_TERMUX: return # Termux users should use 'pkg' for cryptography
    
    # Check if we are already in a venv
    if hasattr(sys, 'real_prefix') or (sys.base_prefix != sys.prefix):
        return
        
    print("Checking virtual environment...")
    venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe") if platform.system() == "Windows" else os.path.join(VENV_DIR, "bin", "python")
    
    if not os.path.exists(venv_python):
        print("🛠️ Creating virtual environment...")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])
            print("Successfully created venv.")
        except Exception as e:
            print(f"Error creating venv: {e}")
            return # Fallback to global python
            
    # Re-run the script using the venv's python
    print("Switching to virtual environment...")
    cmd = [venv_python, __file__] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))

def check_dependencies(is_termux):
    print("Checking dependencies...")
    required = ["cryptography", "rich", "prompt_toolkit"]
    missing = []
    
    for lib in required:
        try:
            __import__(lib)
        except ImportError:
            missing.append(lib)
            
    if missing:
        print(f"Missing libraries: {', '.join(missing)}")
        if is_termux and "cryptography" in missing:
            print("\n[!] TERMUX ERROR: cryptography must be installed via 'pkg'.")
            print("Please run: pkg update && pkg install python-cryptography")
            print("Then run this launcher again.\n")
            sys.exit(1)
            
        print("Attempting to install via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("Successfully installed dependencies.")
        except Exception as e:
            print(f"\nError installing dependencies: {e}")
            if is_termux:
                print("Tip: If pip fails, try 'pkg update' then 'pkg install python-cryptography'.")
                print("For other libraries: pip install rich prompt_toolkit")
            else:
                print("Please run: pip install " + " ".join(required))
            sys.exit(1)

def detect_platform():
    if IS_TERMUX: return "Android (Termux)"
    return platform.system()

def check_system_tools(os_name):
    print(f"Detected Platform: {os_name}")
    if os_name == "Linux":
        if not shutil.which("bluetoothctl"):
            print("Warning: 'bluetoothctl' not found. Please install 'bluez' for Bluetooth support.")
    elif os_name == "Android (Termux)":
        if not shutil.which("termux-bluetooth-scan"):
            print("Warning: 'termux-api' components not found. Scanning may be limited.")
            print("Suggestion: pkg install termux-api")

def main():
    print("--- 🔒 ChatApp Launcher ---")
    
    # Platform-specific auto-setup
    ensure_venv()
    
    os_name = detect_platform()
    is_termux = os_name == "Android (Termux)"
    
    check_system_tools(os_name)
    check_dependencies(is_termux)
    
    print("\nStarting ChatApp...\n")
    
    cmd = [sys.executable, "chat.py"] + sys.argv[1:]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
