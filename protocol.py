import crypto
import trust
import struct

PROTOCOL_VERSION = 1

class ChatProtocol:
    def __init__(self, transport, peer_mac):
        self.transport = transport
        self.peer_mac = peer_mac
        self.session_key = None
        self.my_public_key_bytes = None
        self.peer_public_key_bytes = None
        self.safety_number = None
        self.trust_status = "new"

    def handshake(self):
        """
        Executes the X25519 handshake and verifies peer trust.
        Also verifies protocol version.
        Returns the trust status: "trusted", "new", or "untrusted".
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
        my_priv, my_pub = crypto.generate_keypair()
        self.my_public_key_bytes = my_pub.public_bytes_raw()
        
        # Send my public key
        self.transport.send_framed(self.my_public_key_bytes)
        
        # Receive peer's public key
        self.peer_public_key_bytes = self.transport.recv_framed()
        if not self.peer_public_key_bytes:
            raise ConnectionError("Disconnected during handshake (key exchange)")
        
        # Derive shared session key
        self.session_key = crypto.derive_session_key(my_priv, self.peer_public_key_bytes)
        
        # Calculate safety number
        self.safety_number = crypto.get_safety_number(self.my_public_key_bytes, self.peer_public_key_bytes)
        
        # Verify Trust
        self.trust_status = trust.verify_peer(self.peer_mac, self.peer_public_key_bytes)
        print(f"Handshake complete. Trust: {self.trust_status}")
        return self.trust_status

    def mark_as_trusted(self):
        """Manually marks the current peer as trusted."""
        trust.save_trusted_peer(self.peer_mac, self.peer_public_key_bytes)
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
