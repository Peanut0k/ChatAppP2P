import sys
import argparse
import socket
import os
import time
import threading
import platform
import subprocess
import signal
from pathlib import Path

try:
    import transport
    import protocol
    from ui import ChatUI
except ImportError:
    print("❌ Error: Missing dependencies.")
    print("👉 Please use the launcher for your platform:")
    print("   Linux/Android:  ./run.sh")
    print("   Windows:        run.bat")
    import sys
    sys.exit(1)

def cleanup_temp_files():
    """Wipes any orphaned voice or partial files for privacy."""
    try:
        tmp_dir = Path.home() / "Downloads" / "ChatApp"
        if tmp_dir.exists():
            for p in tmp_dir.glob("voice_*.wav"):
                try: p.unlink()
                except: pass
    except: pass

def main():
    parser = argparse.ArgumentParser(description="Offline Encrypted Bluetooth Chat")
    parser.add_argument("--tcp", action="store_true", help="Use TCP fallback (for Android/WiFi)")
    parser.add_argument("--relay", action="store_true", help="Start in Bridge/Relay mode")
    subparsers = parser.add_subparsers(dest="mode", help="Mode: server or client")
    
    server_parser = subparsers.add_parser("server", help="Wait for a friend to connect")
    
    client_parser = subparsers.add_parser("client", help="Connect to a friend")
    client_parser.add_argument("mac", nargs="?", help="MAC address or IP of the server")
    
    args = parser.parse_args()
    
    if args.relay:
        handle_relay()
        sys.exit(0)

    if not args.mode:
        parser.print_help()
        sys.exit(1)
        
    cleanup_temp_files()
    try:
        while True: # Auto-Reconnect Loop
            try:
                if args.mode == "server":
                    trans = transport.start_server(use_tcp=args.tcp)
                    role = "Server"
                    peer_id = "Waiting..." 
                else:
                    mac = args.mac
                    if not mac:
                        devices = transport.scan_for_devices()
                        if not devices:
                            print("No devices found.")
                            return
                        print("\nDiscovered Devices:")
                        for i, (addr, name) in enumerate(devices):
                            print(f"{i+1}. {addr} - {name}")
                        try:
                            choice = int(input("\nSelect a device (number): ")) - 1
                            if 0 <= choice < len(devices):
                                mac = devices[choice][0]
                            else:
                                print("Invalid choice.")
                                return
                        except ValueError:
                            print("Invalid input.")
                            return
                    
                    trans = transport.start_client(mac, use_tcp=args.tcp)
                    role = "Client"
                    peer_id = mac
                    
                # Handshake metadata
                try:
                    peer_info = trans.sock.getpeername()
                    if args.mode == "client":
                        peer_mac = peer_id
                    elif peer_info and len(peer_info) > 0:
                        peer_mac = peer_info[0]
                    else:
                        peer_mac = peer_id
                except Exception:
                    peer_mac = peer_id # Fallback
                proto = protocol.ChatProtocol(trans, peer_mac)
                trust_status = proto.handshake()
                
                # Start UI
                ui = ChatUI(role, peer_mac, proto.safety_number, trust_status)
                
                def mark_trusted_wrapper():
                    proto.mark_as_trusted()
                    ui.trust_status = "trusted"
                    ui.add_message("System", "Peer marked as TRUSTED.")

                def handle_file_send(path, filename, size):
                    # 1. Calculate Hash (Security)
                    ui.add_message("System", f"🛡️ Calculating security fingerprint for {filename}...")
                    import hashlib
                    sha = hashlib.sha256()
                    with open(path, "rb") as f:
                        while chunk := f.read(65536): sha.update(chunk)
                    f_hash = sha.hexdigest()

                    # 2. Start Handshake
                    proto.send_file_start(filename, size, f_hash)
                    progress_id = ui.add_message("System", f"📤 Negotiating connection for {filename}...")
                    
                    # 3. Wait for Resume Offset (Synchronous Handshake)
                    start_wait = time.time()
                    ui.requested_resume_offset = -1 # Special signal
                    while ui.requested_resume_offset == -1 and time.time() - start_wait < 5:
                        time.sleep(0.1)
                    
                    off = ui.requested_resume_offset if ui.requested_resume_offset >= 0 else 0
                    ui.requested_resume_offset = 0 # reset
                    
                    from transport import format_size
                    tot_str = format_size(size)
                    sent_bytes = off
                    last_upd = 0
                    
                    with open(path, "rb") as f:
                        if off > 0:
                            f.seek(off)
                            ui.update_message(progress_id, f"📤 Resuming: {filename} ({format_size(off)} / {tot_str})")
                        else:
                            ui.update_message(progress_id, f"📤 Sending: {filename} (0B / {tot_str})")

                        while True:
                            chunk = f.read(16 * 1024)
                            if not chunk:
                                break
                            proto.send_file_chunk(chunk)
                            sent_bytes += len(chunk)
                            if size > 0:
                                pct = int((sent_bytes / size) * 100)
                                now = time.time()
                                if (pct % 5 == 0) and (now - last_upd > 0.25):
                                    last_upd = now
                                    cur_str = format_size(sent_bytes)
                                    ui.update_message(progress_id, f"📤 Sending: {filename} ({cur_str} / {tot_str}, {pct}%)")
                    
                    proto.send_file_end()

                voice_ctx = {"proc": None, "path": None}

                def handle_voice_record(is_start):
                    import subprocess, os, platform, time
                    from pathlib import Path
                    
                    if is_start:
                        timestamp = int(time.time())
                        out_path = Path.home() / "Downloads" / "ChatApp" / f"voice_{timestamp}.wav"
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        voice_ctx["path"] = out_path
                        
                        try:
                            if os.environ.get("TERMUX_VERSION"):
                                ui.add_message("System", "🎤 Recording via Termux API...")
                                voice_ctx["proc"] = subprocess.Popen(["termux-microphone-record", "-f", str(out_path), "-e", "wav"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            elif platform.system() == "Windows":
                                ui.add_message("System", "🎤 Searching for recording device...")
                                try:
                                    dev_out = subprocess.check_output(["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], stderr=subprocess.STDOUT, text=True)
                                except subprocess.CalledProcessError as e:
                                    dev_out = e.output
                                
                                import re
                                match = re.search(r'"([^"]*)" \(audio\)', dev_out)
                                device_name = match.group(1) if match else "audio=Microphone"
                                if not match:
                                     match = re.search(r'"(.*Microphone.*)"', dev_out)
                                     if match: device_name = match.group(1)

                                ui.add_message("System", f"🎤 Recording via: {device_name}...")
                                voice_ctx["proc"] = subprocess.Popen(["ffmpeg", "-y", "-f", "dshow", "-i", f"audio={device_name}", "-ar", "16000", "-ac", "1", "-t", "60", str(out_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0)
                            elif platform.system() == "Linux":
                                ui.add_message("System", "🎤 Recording via arecord...")
                                voice_ctx["proc"] = subprocess.Popen(["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", str(out_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid if hasattr(os, 'setsid') else None)
                            else:
                                ui.add_message("System", "⚠️ Voice recording not yet supported on this platform.")
                                ui.is_recording = False
                                return
                        except Exception as e:
                            ui.add_message("System", f"❌ Recording failed to start: {e}")
                            ui.is_recording = False
                    else:
                        # Stop recording
                        if voice_ctx["proc"] or os.environ.get("TERMUX_VERSION"):
                            try:
                                if os.environ.get("TERMUX_VERSION"):
                                    subprocess.run(["termux-microphone-record", "-q"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    time.sleep(0.5)
                                else:
                                    # Use psutil for robust termination of the process and its children
                                    try:
                                        import psutil
                                        parent = psutil.Process(voice_ctx["proc"].pid)
                                        for child in parent.children(recursive=True):
                                            child.terminate()
                                        parent.terminate()
                                    except ImportError:
                                        # Fallback if psutil not available yet
                                        if platform.system() == "Windows":
                                            subprocess.run(["taskkill", "/F", "/T", "/PID", str(voice_ctx["proc"].pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                        else:
                                            import signal
                                            os.killpg(os.getpgid(voice_ctx["proc"].pid), signal.SIGINT)
                                    
                                    voice_ctx["proc"].wait(timeout=2)
                                
                                ui.add_message("System", "✅ Recording finished! (Purging local copy after send)")
                                
                                path = voice_ctx["path"]
                                time.sleep(0.5)
                                if path and path.exists() and path.stat().st_size > 44:
                                    handle_file_send(str(path), path.name, path.stat().st_size)
                                    
                                    def purge_task(p):
                                        for _ in range(5):
                                            try:
                                                time.sleep(3)
                                                if os.path.exists(p):
                                                    os.remove(p)
                                                    break
                                            except: pass
                                    import threading
                                    threading.Thread(target=purge_task, args=(str(path),), daemon=True).start()
                                else:
                                    ui.add_message("System", "⚠️ Recording was too short or failed.")
                            except Exception as e:
                                ui.add_message("System", f"❌ Error stopping recording: {e}")
                            finally:
                                voice_ctx["proc"] = None

                ui.start(
                    send_callback=lambda text: proto.send_message(text),
                    receive_callback=lambda: proto.receive_message(),
                    trust_callback=mark_trusted_wrapper,
                    typing_callback=lambda is_typing: proto.send_typing(is_typing),
                    file_send_callback=handle_file_send,
                    ack_callback=lambda mid: proto.send_read_ack(mid),
                    voice_record_callback=handle_voice_record,
                    resume_callback=lambda off: proto.send_file_resume(off)
                )
                
                # If UI exits normally (via /quit), break out of loop
                if ui._stop_event.is_set():
                    break

            except (ConnectionError, socket.error) as e:
                print(f"\nConnection lost: {e}. Retrying in 5 seconds...")
                import time
                time.sleep(5)
                continue
            finally:
                if 'trans' in locals():
                    trans.close()
        
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\n⚠️ App Stopped: {e}")
    finally:
        cleanup_temp_files()
        if 'trans' in locals():
            trans.close()

def handle_relay():
    import transport, threading
    print("🕸️ Starting Mesh Relay (Bridge Mode)...")
    
    # In this experimental mode, we bridge Bluetooth to TCP
    try:
        print("1. Waiting for Bluetooth client...")
        bt_trans = transport.start_server(use_tcp=False)
        print("✅ Bluetooth client connected.")
        
        print("2. Waiting for TCP client...")
        tcp_trans = transport.start_server(use_tcp=True)
        print("✅ TCP client connected.")
        
        print("\n🚀 Bridge active! Relaying data...")
        
        def pipe(source, target, label):
            try:
                while True:
                    data = source.sock.recv(65536) # Read raw chunks for efficiency in relay
                    if not data: break
                    target.sock.sendall(data)
            except: pass
            print(f"⚠️ {label} connection lost.")

        t1 = threading.Thread(target=pipe, args=(bt_trans, tcp_trans, "BT -> TCP"), daemon=True)
        t2 = threading.Thread(target=pipe, args=(tcp_trans, bt_trans, "TCP -> BT"), daemon=True)
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
    except Exception as e:
        print(f"❌ Relay Error: {e}")

if __name__ == "__main__":
    main()
