# 🔒 Offline Encrypted Bluetooth Chat

A secure, peer-to-peer chat application that works without WiFi or Internet.

## Features
- **Zero Network Dependency**: Uses Bluetooth RFCOMM (no router/wifi needed).
- **Cross-Platform**: Works on **Windows 11**, **Android (Termux)**, **Debian**, Arch, and Ubuntu.
- **Easy Launch**: Simple `python3 run.py` handles everything.
- **Auto-Discovery**: Scans for nearby peers automatically (supports `bluetoothctl`, `termux-api`, and PowerShell).
- **TCP Fallback**: Works over Bluetooth Tethering or WiFi if native sockets are restricted (common on Android).

## Setup

1. **Prerequisites**:
   - **Linux**: `bluez` installed.
   - **Windows**: Windows 11 with Bluetooth enabled.
   - **Android**: Install [Termux](https://termux.dev/) and the [Termux:API](https://play.google.com/store/apps/details?id=com.termux.api) app.
   - **Python**: 3.11+

2. **Installation**:
   ```bash
   # Clone the repo and enter the directory
   # Then just run the universal launcher:
   python3 run.py
   ```
   The launcher will automatically install missing Python libraries (`cryptography`, `rich`, `prompt_toolkit`).

## How to Chat

### Step 1: Start the Server (Computer A)
```bash
python3 run.py server
```
*Note: On Android, if Bluetooth fails, it will automatically fallback to TCP mode.*

### Step 2: Start the Client (Computer B)
Scan for the server:
```bash
python3 run.py client
```

### 📱 Android (No-Root) Tips
Android restricts direct Bluetooth access for non-root apps. If native Bluetooth fails:
1. Enable **Bluetooth Tethering** in Android Settings on the Server device.
2. Connect the Client device to the Server's Bluetooth network.
3. Start the server with `python3 run.py --tcp server`.
4. Start the client with `python3 run.py --tcp client [Server_IP]`.

---

## Troubleshooting
- **Termux**: Run `pkg install termux-api` if scanning doesn't work.
- **Windows**: Ensure Bluetooth is "Discoverable" in Windows Settings.
