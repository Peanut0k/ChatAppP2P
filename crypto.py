import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from pathlib import Path

IDENTITY_FILE = Path.home() / ".config" / "chatapp" / "identity.key"

def get_device_identity():
    """Returns (private_key, public_key) for the device, generating if needed."""
    if not IDENTITY_FILE.exists():
        IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
        private_key = x25519.X25519PrivateKey.generate()
        with open(IDENTITY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            ))
    else:
        with open(IDENTITY_FILE, "rb") as f:
            private_key = x25519.X25519PrivateKey.from_private_bytes(f.read())
    
    return private_key, private_key.public_key()

def generate_keypair():
    """Generates an ephemeral X25519 private and public key."""
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key

def derive_session_key(private_key, peer_public_key_bytes):
    """
    Derives a 32-byte session key using ECDH and HKDF-SHA256.
    """
    peer_public_key = x25519.X25519PublicKey.from_public_bytes(peer_public_key_bytes)
    shared_key = private_key.exchange(peer_public_key)
    
    # Derive a session key from the shared secret
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"offline-chat-session-key",
    ).derive(shared_key)

def encrypt(key, plaintext):
    """
    Encrypts plaintext using ChaCha20-Poly1305.
    Returns nonce + ciphertext + tag.
    """
    aead = ChaCha20Poly1305(key)
    nonce = os.urandom(12)
    ciphertext = aead.encrypt(nonce, plaintext.encode() if isinstance(plaintext, str) else plaintext, None)
    return nonce + ciphertext

def decrypt(key, data):
    """
    Decrypts data (nonce + ciphertext + tag) using ChaCha20-Poly1305.
    Returns plaintext as bytes.
    """
    if len(data) < 12:
        raise ValueError("Ciphertext too short (missing nonce)")
    
    nonce = data[:12]
    ciphertext = data[12:]
    aead = ChaCha20Poly1305(key)
    return aead.decrypt(nonce, ciphertext, None)

def get_safety_number(pub_a_bytes, pub_b_bytes):
    """
    Generates a 6-word safety number (SAS) from both public keys.
    This is deterministic regardless of who is side A or side B.
    """
    # Sort keys to ensure both sides generate the same hash
    ordered_keys = b"".join(sorted([pub_a_bytes, pub_b_bytes]))
    digest = hashes.Hash(hashes.SHA256())
    digest.update(ordered_keys)
    h = digest.finalize()
    
    # Simple wordlist for SAS (Short Authentication String)
    # In a production app, use PGP word list or BIP39
    wordlist = [
        "apple", "beach", "cloud", "dance", "eagle", "flame", "grape", "heart",
        "igloo", "joker", "koala", "lemon", "melon", "night", "ocean", "pearl",
        "queen", "river", "stone", "tiger", "unity", "valve", "whale", "xenon",
        "yacht", "zebra", "atlas", "bravo", "cycle", "delta", "echo", "frost"
    ]
    
    indices = [
        (h[0] << 8 | h[1]) % len(wordlist),
        (h[2] << 8 | h[3]) % len(wordlist),
        (h[4] << 8 | h[5]) % len(wordlist),
        (h[6] << 8 | h[7]) % len(wordlist),
        (h[8] << 8 | h[9]) % len(wordlist),
        (h[10] << 8 | h[11]) % len(wordlist),
    ]
    
    return "-".join([wordlist[i] for i in indices])

if __name__ == "__main__":
    # Quick self-test
    priv1, pub1 = generate_keypair()
    priv2, pub2 = generate_keypair()
    
    pub1_bytes = pub1.public_bytes_raw()
    pub2_bytes = pub2.public_bytes_raw()
    
    key1 = derive_session_key(priv1, pub2_bytes)
    key2 = derive_session_key(priv2, pub1_bytes)
    
    assert key1 == key2
    print("Key exchange success!")
    
    msg = "Hello, CIA!"
    encrypted = encrypt(key1, msg)
    decrypted = decrypt(key2, encrypted)
    assert decrypted.decode() == msg
    print(f"Encryption success: {msg} -> {encrypted.hex()[:20]}... -> {decrypted.decode()}")
    
    sas1 = get_safety_number(pub1_bytes, pub2_bytes)
    sas2 = get_safety_number(pub2_bytes, pub1_bytes)
    assert sas1 == sas2
    print(f"Safety Number: {sas1}")
