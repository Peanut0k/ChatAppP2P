import sys
import argparse
import transport
import protocol
from ui import ChatUI

def main():
    parser = argparse.ArgumentParser(description="Offline Encrypted Bluetooth Chat")
    parser.add_argument("--tcp", action="store_true", help="Use TCP fallback (for Android/WiFi)")
    subparsers = parser.add_subparsers(dest="mode", help="Mode: server or client")
    
    server_parser = subparsers.add_parser("server", help="Wait for a friend to connect")
    
    client_parser = subparsers.add_parser("client", help="Connect to a friend")
    client_parser.add_argument("mac", nargs="?", help="MAC address or IP of the server")
    
    args = parser.parse_args()
    
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
                    
                # Handshake
                try:
                    peer_info = trans.sock.getpeername()
                    peer_mac = peer_id if args.mode == "client" else peer_info[0]
                except:
                    peer_mac = peer_id # Fallback
                proto = protocol.ChatProtocol(trans, peer_mac)
                trust_status = proto.handshake()
                
                # Start UI
                ui = ChatUI(role, peer_mac, proto.safety_number, trust_status)
                
                def mark_trusted_wrapper():
                    proto.mark_as_trusted()
                    ui.trust_status = "trusted"
                    ui.add_message("System", "Peer marked as TRUSTED.")

                ui.start(
                    send_callback=lambda text: proto.send_message(text),
                    receive_callback=lambda: proto.receive_message(),
                    trust_callback=mark_trusted_wrapper,
                    typing_callback=lambda is_typing: proto.send_typing(is_typing)
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
        print(f"\nError: {e}")
    finally:
        if 'trans' in locals():
            trans.close()

if __name__ == "__main__":
    main()
