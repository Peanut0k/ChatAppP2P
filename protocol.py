import crypto

class ChatProtocol:
    def __init__(self, transport):
        self.transport = transport
        self.session_key = None
        self.my_public_key_bytes = None
        self.peer_public_key_bytes = None
        self.safety_number = None

    def handshake(self):
        """
        Executes the X25519 handshake over the transport.
        1. Generates ephemeral keypair.
        2. Sends public key.
        3. Receives peer's public key.
        4. Derives session key and safety number.
        """
        print("Handshaking...")
        my_priv, my_pub = crypto.generate_keypair()
        self.my_public_key_bytes = my_pub.public_bytes_raw()
        
        # Send my public key
        self.transport.send_framed(self.my_public_key_bytes)
        
        # Receive peer's public key
        self.peer_public_key_bytes = self.transport.recv_framed()
        if not self.peer_public_key_bytes:
            raise ConnectionError("Disconnected during handshake")
        
        # Derive shared session key
        self.session_key = crypto.derive_session_key(my_priv, self.peer_public_key_bytes)
        
        # Calculate safety number for verbal verification
        self.safety_number = crypto.get_safety_number(self.my_public_key_bytes, self.peer_public_key_bytes)
        print(f"Handshake complete. Safety Number: {self.safety_number}")

    def send_message(self, text):
        """Encrypts and sends a message."""
        if not self.session_key:
            raise RuntimeError("Handshake not completed")
        
        encrypted = crypto.encrypt(self.session_key, text)
        self.transport.send_framed(encrypted)

    def receive_message(self):
        """Receives and decrypts a message."""
        if not self.session_key:
            raise RuntimeError("Handshake not completed")
        
        encrypted = self.transport.recv_framed()
        if encrypted is None:
            return None # Disconnected
            
        decrypted = crypto.decrypt(self.session_key, encrypted)
        return decrypted.decode('utf-8')
