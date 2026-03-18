# 🔒 Offline Encrypted Bluetooth Chat

A secure, peer-to-peer chat application that works without WiFi or Internet.

## Features
- **Zero Network Dependency**: Uses Bluetooth RFCOMM (no router/wifi needed).
- **End-to-End Encryption**: X25519 ECDH for key exchange and ChaCha20-Poly1305 for messaging.
- **Forward Secrecy**: New session keys are generated for every connection.
- **MITM Protection**: 6-word "Safety Number" for verbal verification.
- **Beautiful UI**: Rich terminal interface with message history.

## Setup

1. **Prerequisites**:
   - Linux (Arch, Ubuntu, Fedora, etc.)
   - Bluetooth adapter (Internal or USB dongle)
   - Python 3.11+

2. **Installation**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install cryptography rich
   ```

## How to Chat

### Step 1: Find your MAC Address
Run this on the computer that will be the **Server**:
```bash
hciconfig
```
Look for `BD Address: AA:BB:CC:DD:EE:FF`. This is your Bluetooth MAC.

### Step 2: Start the Server (Computer A)
```bash
python3 chat.py server
```

### Step 3: Start the Client (Computer B)
Replace `AA:BB:CC:DD:EE:FF` with the server's MAC address:
```bash
python3 chat.py client AA:BB:CC:DD:EE:FF
```

### Step 4: Verify Safety Number
Once connected, both screens will show a **6-word safety number**. 
Read these aloud to your friend. If they match, your connection is secure and cannot be intercepted (not even by the CIA).

## Troubleshooting
- **Permission Denied**: Make sure you are in the `bluetooth` group or run with `sudo`.
- **Soft Blocked**: The app tries to unblock via `rfkill`, but you can also run `sudo rfkill unblock bluetooth` manually.
- **Connection Refused**: Ensure the server is running and the Bluetooth adapter is powered on (`bluetoothctl power on`).
