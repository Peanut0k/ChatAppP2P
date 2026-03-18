import socket
import struct
import subprocess
import os
import sys
import platform
import re

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_TERMUX = os.environ.get("TERMUX_VERSION") is not None

# Socket constants
if IS_WINDOWS:
    AF_BLUETOOTH = getattr(socket, "AF_BTH", 32)
    BTPROTO_RFCOMM = 3
elif IS_TERMUX:
    # Termux doesn't always have AF_BLUETOOTH in the socket module
    AF_BLUETOOTH = getattr(socket, "AF_BLUETOOTH", 31)
    BTPROTO_RFCOMM = getattr(socket, "BTPROTO_RFCOMM", 3)
else:
    AF_BLUETOOTH = socket.AF_BLUETOOTH
    BTPROTO_RFCOMM = socket.BTPROTO_RFCOMM

RFCOMM_CHANNEL = 1
TCP_PORT = 50001

class Transport:
    def send_framed(self, data: bytes): raise NotImplementedError()
    def recv_framed(self) -> bytes: raise NotImplementedError()
    def close(self): raise NotImplementedError()

class BluetoothTransport(Transport):
    def __init__(self, sock=None):
        self.sock = sock

    def send_framed(self, data: bytes):
        length = len(data)
        header = struct.pack(">I", length)
        self.sock.sendall(header + data)

    def recv_framed(self) -> bytes:
        header = self._recv_exact(4)
        if not header: return None
        length = struct.unpack(">I", header)[0]
        return self._recv_exact(length)

    def _recv_exact(self, n):
        data = b""
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
                if not packet: return None
                data += packet
            except socket.error: return None
        return data

    def close(self):
        if self.sock:
            try: self.sock.close()
            except: pass

class TCPTransport(BluetoothTransport):
    """Same framing logic as Bluetooth, but over TCP."""
    pass

def unblock_bluetooth():
    if IS_WINDOWS or IS_TERMUX: return 
    try:
        subprocess.run(["sudo", "rfkill", "unblock", "bluetooth"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception: pass

def get_local_adapter_mac():
    if IS_WINDOWS or IS_TERMUX: return "00:00:00:00:00:00" 
    try:
        # Use 'bluetoothctl show' and look for the MAC address
        output = subprocess.check_output(["bluetoothctl", "show"], text=True)
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("Controller"):
                parts = line.split()
                if len(parts) > 1:
                    return parts[1]
    except Exception: pass
    return "00:00:00:00:00:00"

def start_server(use_tcp=False):
    if use_tcp: return start_tcp_server()
    
    unblock_bluetooth()
    mac = get_local_adapter_mac()
    bind_addr = "" if IS_WINDOWS else mac
    try:
        server_sock = socket.socket(AF_BLUETOOTH, socket.SOCK_STREAM, BTPROTO_RFCOMM)
        server_sock.bind((bind_addr, RFCOMM_CHANNEL))
        server_sock.listen(1)
        print(f"Waiting for Bluetooth connection on channel {RFCOMM_CHANNEL}...")
        client_sock, client_info = server_sock.accept()
        return BluetoothTransport(client_sock)
    except Exception as e:
        print(f"Bluetooth Server Error: {e}. Falling back to TCP...")
        return start_tcp_server()

def start_client(server_mac, use_tcp=False):
    if use_tcp or "." in server_mac: # Detect IP address
        return start_tcp_client(server_mac)
        
    unblock_bluetooth()
    client_sock = socket.socket(AF_BLUETOOTH, socket.SOCK_STREAM, BTPROTO_RFCOMM)
    client_sock.connect((server_mac, RFCOMM_CHANNEL))
    return BluetoothTransport(client_sock)

def start_tcp_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind to all interfaces (works over Bluetooth Tethering)
    server_sock.bind(("0.0.0.0", TCP_PORT))
    server_sock.listen(1)
    print(f"Waiting for TCP connection on port {TCP_PORT}...")
    print("Tip: Use Bluetooth Tethering or Local WiFi if native Bluetooth fails.")
    client_sock, client_info = server_sock.accept()
    return TCPTransport(client_sock)

def start_tcp_client(server_ip):
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect((server_ip, TCP_PORT))
    return TCPTransport(client_sock)

def scan_for_devices():
    if IS_WINDOWS: return _scan_windows()
    if IS_TERMUX: return _scan_termux()
    return _scan_linux()

def _scan_termux():
    print("Scanning via termux-api...")
    try:
        output = subprocess.check_output(["termux-bluetooth-scan"], text=True)
        # termux-bluetooth-scan returns a JSON list
        import json
        devices_data = json.loads(output)
        return [(d["address"], d.get("name", "Unknown")) for d in devices_data]
    except Exception as e:
        print(f"Termux scan error: {e}. Make sure 'termux-api' is installed.")
        return []

def _scan_linux():
    print("Scanning via bluetoothctl...")
    try:
        # Start scan
        subprocess.run(["bluetoothctl", "scan", "on"], timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Get devices
        output = subprocess.check_output(["bluetoothctl", "devices"], text=True)
        devices = []
        for line in output.split("\n"):
            # Format: Device AA:BB:CC:DD:EE:FF Name
            match = re.search(r"Device (([0-9A-F]{2}:?){6}) (.*)", line, re.I)
            if match:
                devices.append((match.group(1), match.group(3)))
        return devices
    except Exception as e:
        print(f"Linux scan error: {e}")
        return []

def _scan_windows():
    print("Scanning via PowerShell...")
    try:
        # Use PowerShell to find paired or nearby devices
        # This snippet looks for devices in the PnP list (mostly paired)
        # For full discovery, real Winsock calls are needed, but this is a good start for Win11
        cmd = "Get-PnpDevice -Class Bluetooth | Select-Object FriendlyName, InstanceId"
        output = subprocess.check_output(["powershell", "-Command", cmd], text=True)
        devices = []
        for line in output.split("\n"):
            line = line.strip()
            if not line or "FriendlyName" in line or "---" in line:
                continue
            # InstanceId often contains the MAC: BTHEN\DEV_AABBCCDDEEFF\...
            parts = line.split()
            name = " ".join(parts[:-1])
            iid = parts[-1]
            mac_match = re.search(r"DEV_([0-9A-F]{12})", iid, re.I)
            if mac_match:
                raw_mac = mac_match.group(1)
                # Format as AA:BB:CC:DD:EE:FF
                mac = ":".join(raw_mac[i:i+2] for i in range(0, 12, 2))
                devices.append((mac, name))
        return devices
    except Exception as e:
        print(f"Windows scan error: {e}")
        return []

if __name__ == "__main__":
    # Test framing using a mock loopback socket pair if desired
    # But for now, we'll just test by running the script
    pass
