# 🔒 Offline Encrypted P2P Chat (v3.0)

A secure, "flawless" peer-to-peer chat application that works without WiFi or Internet.

## ✨ New in Version 3.1
- **🎙️ Pro Walkie-Talkie**: `/voice` is now a toggle! Start and stop recording whenever you want.
- **� Unique Files**: No more duplicate or overwritten voice memos.
- **⚡ Async UI**: Recording and playback no longer freeze the chat.

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

- `/send`: Open the **Built-in File Explorer** to browse and select files.
- `/send <path>`: Send a specific file by its full path.
- `/voice`: Toggle Walkie-Talkie recording (Press **Enter** to stop instantly).
- `/trust`: Mark current peer as trusted.
- `/quit`: Exit the app.
- `/help`: Show all commands.

### 📁 Using the File Explorer
1. Type `/send` and press **Enter**.
2. **↑ / ↓ Arrows**: Move the selection pointer.
3. **[Enter]**: Enter a folder or select a file to send.
4. **[Esc]**: Close the explorer and return to chat.

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
