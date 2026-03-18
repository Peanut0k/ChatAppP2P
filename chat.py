import sys
import argparse
import socket
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
                    chunk_size = 32 * 1024 # 32KB chunks
                    proto.send_file_start(filename, size)
                    with open(path, "rb") as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            proto.send_file_chunk(chunk)
                    proto.send_file_end()

                voice_ctx = {"proc": None, "path": None}

                def handle_voice_record(is_start):
                    import subprocess, os, platform, signal, time
                    from pathlib import Path
                    
                    if is_start:
                        timestamp = int(time.time())
                        out_path = Path.home() / "Downloads" / "ChatApp" / f"voice_{timestamp}.wav"
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        voice_ctx["path"] = out_path
                        
                        try:
                            ui.add_message("System", "🎤 Recording... (Type /voice or press Enter to stop)")
                            if os.environ.get("TERMUX_VERSION"):
                                 # Termux (Android)
                                 voice_ctx["proc"] = subprocess.Popen(["termux-microphone-record", "-f", str(out_path)], preexec_fn=os.setsid)
                            elif platform.system() == "Linux":
                                 # Linux (ALSA)
                                 voice_ctx["proc"] = subprocess.Popen(["arecord", "-f", "cd", str(out_path)], preexec_fn=os.setsid)
                            else:
                                 ui.add_message("System", "⚠️ Voice recording not yet supported on this platform.")
                                 ui.is_recording = False
                                 return
                        except Exception as e:
                            ui.add_message("System", f"❌ Recording failed to start: {e}")
                            ui.is_recording = False
                    else:
                        # Stop recording
                        if voice_ctx["proc"]:
                            try:
                                os.killpg(os.getpgid(voice_ctx["proc"].pid), signal.SIGINT)
                                voice_ctx["proc"].wait(timeout=2)
                                ui.add_message("System", "✅ Recording finished!")
                                
                                path = voice_ctx["path"]
                                if path.exists():
                                    handle_file_send(str(path), path.name, path.stat().st_size)
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
                    voice_record_callback=handle_voice_record
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
