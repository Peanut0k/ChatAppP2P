# 🔒 Offline Encrypted Bluetooth Chat

A secure, peer-to-peer chat application that works without WiFi or Internet.

## Features
- **Zero Network Dependency**: Uses Bluetooth RFCOMM (no router/wifi needed).
- **Cross-Platform**: Works on **Windows 11**, **Android (Termux)**, **Debian**, Arch, and Ubuntu.
- **Easy Launch**: Simple `python3 run.py` handles everything.
- **Auto-Discovery**: Scans for nearby peers automatically (supports `bluetoothctl`, `termux-api`, and PowerShell).
- **TCP Fallback**: Works over Bluetooth Tethering or WiFi if native sockets are restricted (common on Android).

## 🚀 Zero-Config Setup

The ChatApp now handles all its own dependencies and environments. You don't need to manually create virtual environments or install Python packages.

### 1. Prerequisites
- **Python**: 3.11 or higher installed on your system.
- **Bluetooth**: Hardware enabled and discoverable.

### 2. Launch the App
Clone the repository and run the launcher for your operating system:

*   **Linux / Android (Termux)**:
    ```bash
    ./run.sh server
    ```
*   **Windows**:
    ```cmd
    run.bat server
    ```
*   **Universal**:
    ```bash
    python3 run.py server
    ```
*The launcher will automatically create a virtual environment, install dependencies (including `pkg` dependencies on Termux), and start the app.*

---

## 💬 How to Chat

### Step 1: Start the Server (Computer A)
Run the launcher in `server` mode:
```bash
./run.sh server
```

### Step 2: Start the Client (Computer B)
Run the launcher in `client` mode. If you don't provide a MAC address, it will automatically scan for nearby devices:
```bash
./run.sh client
```
*Or connect directly:*
```bash
./run.sh client AA:BB:CC:DD:EE:FF
```

---

## 📱 Android (Termux) Support
Android restricts direct Bluetooth access for non-root apps. If native Bluetooth fails:
1. Enable **Bluetooth Tethering** in Android Settings on the Server device.
2. Connect the Client device to the Server's Bluetooth network.
3. Use the `--tcp` flag:
   - Server: `./run.sh --tcp server`
   - Client: `./run.sh --tcp client [Server_IP]`

---

## 🛠️ Troubleshooting
- **Linux**: Ensure your user is in the `bluetooth` group or use `sudo ./run.sh`.
- **Windows**: Make sure Bluetooth is set to "Discoverable" in Windows settings.
- **Termux**: If scanning fails, ensure you have the **Termux:API** app installed from the Play Store/F-Droid.
