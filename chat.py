import sys
import argparse
import transport
import protocol
from ui import ChatUI

def main():
    parser = argparse.ArgumentParser(description="Offline Encrypted Bluetooth Chat")
    subparsers = parser.add_subparsers(dest="mode", help="Mode: server or client")
    
    server_parser = subparsers.add_parser("server", help="Wait for a friend to connect")
    
    client_parser = subparsers.add_parser("client", help="Connect to a friend")
    client_parser.add_argument("mac", help="MAC address of the server (e.g. 08:8E:90:8A:05:8D)")
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        sys.exit(1)
        
    try:
        if args.mode == "server":
            trans = transport.start_server()
            role = "Server"
            peer_id = "Waiting..." # Will be updated after handshake
        else:
            trans = transport.start_client(args.mac)
            role = "Client"
            peer_id = args.mac
            
        # Handshake
        proto = protocol.ChatProtocol(trans)
        proto.handshake()
        
        # Start UI
        ui = ChatUI(role, peer_id if args.mode == "client" else trans.sock.getpeername()[0], proto.safety_number)
        
        ui.start(
            send_callback=lambda text: proto.send_message(text),
            receive_callback=lambda: proto.receive_message()
        )
        
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        if 'trans' in locals():
            trans.close()

if __name__ == "__main__":
    main()
