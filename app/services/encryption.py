import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import settings


# MASTER_KEY protects per-user DEKs; images are encrypted with DEK.
# Accept either a valid Fernet key or derive one deterministically from the provided string.
_raw_key = settings.MASTER_KEY
if isinstance(_raw_key, str):
    _raw_key_bytes = _raw_key.encode()
else:
    _raw_key_bytes = _raw_key

try:
    _master = Fernet(_raw_key)  # try as-is
except Exception:
    # Derive a valid Fernet key from the provided value (deterministic)
    digest = hashlib.sha256(_raw_key_bytes).digest()  # 32 bytes
    derived_key = base64.urlsafe_b64encode(digest)
    _master = Fernet(derived_key)


def new_data_key() -> bytes:
    return Fernet.generate_key()  # returns base64 urlsafe 32-byte key


def wrap_dek(plain_key_b64: bytes) -> str:
    return _master.encrypt(plain_key_b64).decode()


def unwrap_dek(encrypted_b64: str) -> bytes:
    return _master.decrypt(encrypted_b64.encode())


def fernet_from_dek(dek_b64: bytes) -> Fernet:
    return Fernet(dek_b64)