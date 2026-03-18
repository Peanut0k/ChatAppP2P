import json
import os
from pathlib import Path

TRUST_FILE = Path.home() / ".config" / "chatapp" / "trusted_peers.json"

def _ensure_dir():
    TRUST_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not TRUST_FILE.exists():
        with open(TRUST_FILE, "w") as f:
            json.dump({}, f)

def load_trusted_peers():
    _ensure_dir()
    try:
        with open(TRUST_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_trusted_peer(mac, pub_key_bytes):
    peers = load_trusted_peers()
    peers[mac] = pub_key_bytes.hex()
    with open(TRUST_FILE, "w") as f:
        json.dump(peers, f, indent=2)

def verify_peer(mac, pub_key_bytes):
    """
    Returns:
    - "trusted": If MAC matches stored pub key.
    - "new": If MAC is not in store.
    - "untrusted": If MAC matches a DIFFERENT pub key (Possible MITM!).
    """
    peers = load_trusted_peers()
    if mac not in peers:
        return "new"
    
    stored_hex = peers[mac]
    current_hex = pub_key_bytes.hex()
    
    if stored_hex == current_hex:
        return "trusted"
    else:
        return "untrusted"
