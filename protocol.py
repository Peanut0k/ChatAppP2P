import crypto
import trust
import struct

PROTOCOL_VERSION = 2

class ChatProtocol:
    def __init__(self, transport, peer_mac):
        self.transport = transport
        self.peer_mac = peer_mac
        self.session_key = None
        self.my_id_pub = None
        self.peer_id_pub = None
        self.safety_number = None
        self.trust_status = "new"

    def handshake(self):
        """
        Executes the X25519 handshake and verifies peer trust.
        """
        print("Handshaking...")
        
        # 1. Exchange Versions
        self.transport.send_framed(struct.pack(">I", PROTOCOL_VERSION))
        peer_version_bytes = self.transport.recv_framed()
        if not peer_version_bytes:
            raise ConnectionError("Disconnected during handshake (version exchange)")
        peer_version = struct.unpack(">I", peer_version_bytes)[0]
        
        if peer_version != PROTOCOL_VERSION:
            raise ConnectionError(f"Protocol version mismatch: Mine={PROTOCOL_VERSION}, Peer={peer_version}")

        # 2. Key Exchange
        # Get permanent identity and generate fresh ephemeral key
        id_priv, id_pub = crypto.get_device_identity()
        eph_priv, eph_pub = crypto.generate_keypair()
        
        self.my_id_pub = id_pub.public_bytes_raw()
        my_eph_pub = eph_pub.public_bytes_raw()
        
        # Send Identity + Ephemeral keys (64 bytes total)
        self.transport.send_framed(self.my_id_pub + my_eph_pub)
        
        # Receive Peer's Identity + Ephemeral keys
        peer_keys = self.transport.recv_framed()
        if not peer_keys or len(peer_keys) < 64:
            raise ConnectionError("Disconnected during handshake (key exchange)")
        
        self.peer_id_pub = peer_keys[:32]
        peer_eph_pub = peer_keys[32:64]
        
        # Derive session key from ephemeral keys (Forward Secrecy)
        self.session_key = crypto.derive_session_key(eph_priv, peer_eph_pub)
        
        # Calculate safety number from permanent identity keys
        self.safety_number = crypto.get_safety_number(self.my_id_pub, self.peer_id_pub)
        
        # Verify Trust using the permanent identity
        self.trust_status = trust.verify_peer(self.peer_mac, self.peer_id_pub)
        print(f"Handshake complete. Trust: {self.trust_status}")
        return self.trust_status

    def mark_as_trusted(self):
        """Manually marks the current peer as trusted."""
        trust.save_trusted_peer(self.peer_mac, self.peer_id_pub)
        self.trust_status = "trusted"

    def send_message(self, text):
        """Encrypts and sends a message."""
        self._send_raw(b'\x01' + text.encode('utf-8'))

    def send_typing(self, is_typing):
        """Sends a typing notification."""
        self._send_raw(b'\x02' + (b'\x01' if is_typing else b'\x00'))

    def _send_raw(self, data):
        if not self.session_key:
            raise RuntimeError("Handshake not completed")
        encrypted = crypto.encrypt(self.session_key, data)
        self.transport.send_framed(encrypted)

    def receive_message(self):
        """
        Receives and decrypts a message or control packet.
        Returns (type, content) where type is "text" or "typing".
        """
        if not self.session_key:
            raise RuntimeError("Handshake not completed")
        
        encrypted = self.transport.recv_framed()
        if encrypted is None:
            return None, None
            
        decrypted = crypto.decrypt(self.session_key, encrypted)
        if not decrypted:
            return None, None
            
        msg_type = decrypted[0]
        payload = decrypted[1:]
        
        if msg_type == 1: # Text
            return "text", payload.decode('utf-8')
        elif msg_type == 2: # Typing
            return "typing", payload == b'\x01'
        
        return "unknown", payload
