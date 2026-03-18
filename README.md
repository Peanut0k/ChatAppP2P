# 🔒 Offline Encrypted P2P Chat (v3.0)

A secure, "flawless" peer-to-peer chat application that works without WiFi or Internet.

## ✨ New in Version 3.0
- **📂 File Transfer**: Send any file encrypted over the air (`/send <path>`).
- **🎙️ Walkie-Talkie Mode**: Send 5-second encrypted voice memos (`/voice`).
- **✓ Read Receipts**: Real-time status (✓) when your friend sees your message.
- **🕸️ Mesh Relay**: Bridge connections between Bluetooth and TCP nodes (`--relay`).
- **🛡️ Identity Trust**: Permanent device identities that stick across restarts.

## 🚀 Zero-Config Setup

The ChatApp handles its own environments. **Just run and chat.**

### 1. Prerequisites
- **Python**: 3.11+ installed.
- **Bluetooth**: Hardware enabled and discoverable.

### 2. Launch
Clone and run the launcher for your OS:

- **Linux / Android (Termux)**:
  ```bash
  ./run.sh server  # Run on Computer A
  ./run.sh client  # Run on Computer B (scans automatically)
  ```
- **Windows**:
  ```cmd
  run.bat server
  run.bat client
  ```
- **Bridge / Mesh Mode**:
  ```bash
  ./run.sh --relay
  ```

---

## 💬 In-Chat Commands

- `/send <path>`: Send a file (e.g., `/send ~/myphoto.jpg`).
- `/voice`: Record 5 seconds of audio and send it (auto-plays on receiver).
- `/trust`: Mark a new peer's identity as trusted permanently.
- `/quit`: Exit the app safely.
- `/help`: Show this command list.

---

## 📱 Android (Termux) Support
Android restricts direct Bluetooth for non-root. If scanning fails:
1. Enable **Bluetooth Tethering** on the Server.
2. Connect the Client to the Server's Bluetooth network.
3. Use the `--tcp` flag:
   - Server: `./run.sh --tcp server`
   - Client: `./run.sh --tcp client [Server_IP]`

### Requirements for Android:
Install the **Termux:API** app (Play Store/F-Droid) to enable Bluetooth scanning, microphone recording, and voice playback.

---

## 🛠️ Troubleshooting
- **Permission Denied**: On Linux, ensure you are in the `bluetooth` group or use `sudo ./run.sh`.
- **Identity Warning**: If you see a **🔴 UNTRUSTED** warning, it means someone is intercepting your connection or your friend reinstalled their app. Check your safety numbers!
- **Voice Fails**: On Linux, ensure `alsa-utils` is installed (for `arecord` and `aplay`).
