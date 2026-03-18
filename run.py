import sys
import subprocess
import platform
import os
import shutil

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
            print("Please run: pkg install python-cryptography")
            print("Then run this launcher again.\n")
            sys.exit(1)
            
        print("Attempting to install via pip...")
        try:
            # For Termux, rich and prompt_toolkit work fine via pip
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
    # Check for Termux
    if os.environ.get("TERMUX_VERSION") or os.path.exists("/data/data/com.termux"):
        return "Android (Termux)"
    return platform.system()

def check_system_tools(os_name):
    print(f"Detected Platform: {os_name}")
    if os_name == "Linux":
        if not shutil.which("bluetoothctl"):
            print("Warning: 'bluetoothctl' not found. Please install 'bluez' for Bluetooth support.")
    elif os_name == "Android (Termux)":
        if not shutil.which("termux-bluetooth-scan"):
            print("Warning: 'termux-api' components not found.")
            print("To enable scanning, please run: pkg install termux-api")

def main():
    print("--- 🔒 ChatApp Launcher ---")
    
    os_name = detect_platform()
    is_termux = os_name == "Android (Termux)"
    
    check_system_tools(os_name)
    check_dependencies(is_termux)
    
    print("\nStarting ChatApp...\n")
    
    # Forward all arguments to chat.py
    cmd = [sys.executable, "chat.py"] + sys.argv[1:]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
