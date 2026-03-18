import crypto
import trust
import struct
import time

PROTOCOL_VERSION = 3

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
        """Encrypts and sends a message with a unique ID."""
        # Use nanosecond precision for unique ID, take last 10 digits
        msg_id = str(time.time_ns())[-10:]
        self._send_raw(b'\x01' + msg_id.encode('utf-8') + b':' + text.encode('utf-8'))
        return msg_id

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
            parts = payload.split(b':', 1)
            if len(parts) > 1:
                return "text", (parts[0].decode('utf-8'), parts[1].decode('utf-8'))
            return "text", (None, payload.decode('utf-8'))
        elif msg_type == 2: # Typing
            return "typing", payload == b'\x01'
        elif msg_type == 3: # FILE Metadata
            import json
            return "file_start", json.loads(payload.decode('utf-8'))
        elif msg_type == 4: # FILE Chunk
            return "file_chunk", payload
        elif msg_type == 5: # FILE End
            return "file_end", None
        elif msg_type == 6: # READ Ack
            return "read_ack", payload.decode('utf-8')
        elif msg_type == 7: # FILE Resume Request
            return "file_resume", struct.unpack(">Q", payload)[0]
        elif msg_type == 8: # VOICE Played Ack
            return "voice_ack", payload.decode('utf-8')
        elif msg_type == 9: # VOICE Dismissed
            return "voice_dismiss", payload.decode('utf-8')
        elif msg_type == 10: # FILE Rejected
            return "file_reject", payload.decode('utf-8')
        
        return "unknown", payload

    def send_file_start(self, filename, size, file_hash):
        import json
        meta = json.dumps({"name": filename, "size": size, "sha256": file_hash})
        self._send_raw(b'\x03' + meta.encode('utf-8'))

    def send_file_chunk(self, chunk):
        self._send_raw(b'\x04' + chunk)

    def send_file_end(self):
        self._send_raw(b'\x05' + b'')

    def send_read_ack(self, message_id):
        self._send_raw(b'\x06' + message_id.encode('utf-8'))

    def send_file_resume(self, offset):
        self._send_raw(b'\x07' + struct.pack(">Q", offset))

    def send_voice_ack(self, filename):
        self._send_raw(b'\x08' + filename.encode('utf-8'))

    def send_voice_dismiss(self, filename):
        self._send_raw(b'\x09' + filename.encode('utf-8'))

    def send_file_reject(self, filename):
        self._send_raw(b'\x0a' + filename.encode('utf-8'))
