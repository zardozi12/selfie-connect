import os
import json
import hmac
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Secret for HMAC signing
LINK_HMAC_SECRET = (os.getenv("LINK_HMAC_SECRET") or "dev-secret").encode()

def generate_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)

def encrypt_json(data: dict, key: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypt dict using AES-256-GCM.
    Returns (nonce, ciphertext) bytes.
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, json.dumps(data).encode("utf-8"), associated_data=None)
    return nonce, ct

def decrypt_json(nonce: bytes, ciphertext: bytes, key: bytes) -> dict:
    aesgcm = AESGCM(key)
    pt = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    return json.loads(pt.decode("utf-8"))

def sign_token(b: bytes) -> str:
    mac = hmac.new(LINK_HMAC_SECRET, b, hashlib.sha256).hexdigest()
    return mac

def verify_token(b: bytes, sig: str) -> bool:
    mac = hmac.new(LINK_HMAC_SECRET, b, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sig)