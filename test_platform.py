import os
import platform
import shutil
from pathlib import Path

def test_paths():
    print("--- 📂 Path Verification ---")
    try:
        import crypto
        import trust
        print(f"Identity File: {crypto.IDENTITY_FILE}")
        print(f"Trust File: {trust.TRUST_FILE}")
        
        # Verify they are in the right place for the platform
        if platform.system() == "Windows":
            assert "AppData" in str(crypto.IDENTITY_FILE)
            print("✅ Windows paths use AppData.")
        else:
            assert ".config" in str(crypto.IDENTITY_FILE)
            print("✅ Linux/Unix paths use .config.")
    except Exception as e:
        print(f"❌ Path test failed: {e}")

def test_dependencies():
    print("\n--- 📦 Dependency Verification ---")
    deps = ["ffmpeg", "ffplay", "arecord", "aplay"]
    for dep in deps:
        path = shutil.which(dep)
        status = f"✅ FOUND at {path}" if path else "❌ MISSING"
        print(f"{dep:10}: {status}")
    
    try:
        import psutil
        print(f"psutil    : ✅ FOUND (version {psutil.__version__})")
    except ImportError:
        print("psutil    : ❌ MISSING (Required for robust voice control)")
    
    if os.environ.get("TERMUX_VERSION"):
        print("📱 Environment: Termux (Android)")
        api_tools = ["termux-microphone-record", "termux-bluetooth-scan"]
        for tool in api_tools:
            path = shutil.which(tool)
            status = f"✅ FOUND at {path}" if path else "❌ MISSING"
            print(f"{tool:25}: {status}")

def test_crypto():
    print("\n--- 🔐 Crypto Verification ---")
    try:
        import crypto
        priv, pub = crypto.get_device_identity()
        print(f"✅ Device Identity generated/loaded. PubKey Hash: {pub.public_bytes_raw().hex()[:10]}...")
        
        # Test encryption/decryption
        key = os.urandom(32)
        msg = "Test transmission 123"
        enc = crypto.encrypt(key, msg)
        dec = crypto.decrypt(key, enc)
        assert dec.decode() == msg
        print("✅ Encryption/Decryption works.")
    except Exception as e:
        print(f"❌ Crypto test failed: {e}")

if __name__ == "__main__":
    print(f"Running diagnostics on {platform.system()} {platform.release()}...\n")
    test_paths()
    test_dependencies()
    test_crypto()
    print("\n--- 🏁 Verification Complete ---")
