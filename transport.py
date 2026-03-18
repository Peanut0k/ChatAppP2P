import socket
import struct
import subprocess
import os

# Default RFCOMM port (channel 1)
RFCOMM_CHANNEL = 1

def unblock_bluetooth():
    """Attempts to unblock Bluetooth using rfkill."""
    try:
        subprocess.run(["sudo", "rfkill", "unblock", "bluetooth"], check=False)
    except Exception as e:
        print(f"Warning: Could not unblock bluetooth: {e}")

def get_local_adapter_mac():
    """Returns the MAC address of the first Bluetooth adapter (hci0)."""
    try:
        output = subprocess.check_output(["hciconfig"], text=True)
        for line in output.split("\n"):
            if "BD Address" in line:
                return line.split("BD Address:")[1].split()[0].strip()
    except Exception:
        pass
    return "00:00:00:00:00:00"

class BluetoothTransport:
    def __init__(self, sock=None):
        self.sock = sock

    def send_framed(self, data: bytes):
        """Sends data prefixed with its length (4-byte big-endian)."""
        length = len(data)
        header = struct.pack(">I", length)
        self.sock.sendall(header + data)

    def recv_framed(self) -> bytes:
        """Receives length-prefixed data."""
        header = self._recv_exact(4)
        if not header:
            return None
        length = struct.unpack(">I", header)[0]
        return self._recv_exact(length)

    def _recv_exact(self, n):
        """Helper to receive exactly n bytes from the socket."""
        data = b""
        while len(data) < n:
            packet = self.sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def close(self):
        if self.sock:
            self.sock.close()

def start_server():
    """Starts a Bluetooth RFCOMM server and waits for one connection."""
    print("Unblocking Bluetooth...")
    unblock_bluetooth()
    
    mac = get_local_adapter_mac()
    print(f"Server started. Local MAC: {mac}")
    print(f"Waiting for connection on RFCOMM channel {RFCOMM_CHANNEL}...")
    
    server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    server_sock.bind((mac, RFCOMM_CHANNEL))
    server_sock.listen(1)
    
    client_sock, client_info = server_sock.accept()
    print(f"Accepted connection from {client_info}")
    
    return BluetoothTransport(client_sock)

def start_client(server_mac):
    """Connects to a Bluetooth RFCOMM server at the given MAC address."""
    print("Unblocking Bluetooth...")
    unblock_bluetooth()
    
    print(f"Connecting to {server_mac} on channel {RFCOMM_CHANNEL}...")
    client_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    client_sock.connect((server_mac, RFCOMM_CHANNEL))
    print("Connected!")
    
    return BluetoothTransport(client_sock)

if __name__ == "__main__":
    # Test framing using a mock loopback socket pair if desired
    # But for now, we'll just test by running the script
    pass
