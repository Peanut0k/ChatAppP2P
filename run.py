import sys
import subprocess
import platform
import os

def check_dependencies():
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
        print("Installing now...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("Successfully installed dependencies.")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            print("Please run: pip install " + " ".join(required))
            sys.exit(1)

def detect_platform():
    system = platform.system()
    # Check for Termux
    if os.environ.get("TERMUX_VERSION"):
        return "Android (Termux)"
    return system

def check_system_tools(os_name):
    print(f"Detected Platform: {os_name}")
    if os_name == "Linux":
        if subprocess.run(["which", "bluetoothctl"], capture_output=True).returncode != 0:
            print("Warning: 'bluetoothctl' not found. Please install 'bluez' for Bluetooth support.")
    elif os_name == "Android (Termux)":
        if subprocess.run(["which", "termux-bluetooth-scan"], capture_output=True).returncode != 0:
            print("Warning: 'termux-api' not found. Please run: pkg install termux-api")

def main():
    print("--- 🔒 ChatApp Launcher ---")
    
    os_name = detect_platform()
    check_system_tools(os_name)
    check_dependencies()
    
    print("\nStarting ChatApp...\n")
    
    # Forward all arguments to chat.py
    cmd = [sys.executable, "chat.py"] + sys.argv[1:]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
