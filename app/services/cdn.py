import os
import time
import hmac
import hashlib
import base64
from urllib.parse import urlencode

CDN_BASE_URL = os.getenv("CDN_BASE_URL", "")
CDN_SIGNING_KEY = os.getenv("CDN_SIGNING_KEY", "")


def cdn_url(storage_key: str, *, expires_s: int = None, params: dict = None) -> str:
    """Generate CDN URL with optional signing"""
    base = CDN_BASE_URL.rstrip("/")
    if not base:
        # Fallback: return direct API endpoint when CDN not configured
        from app.config import settings
        api_base = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
        return f"{api_base}/images/{storage_key}/view"
    path = f"/{storage_key.lstrip('/')}"
    query = dict(params or {})
    
    if expires_s and CDN_SIGNING_KEY:
        exp = int(time.time()) + int(expires_s)
        sig_payload = f"{path}{exp}".encode()
        sig = hmac.new(CDN_SIGNING_KEY.encode(), sig_payload, hashlib.sha256).digest()
        b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
        query.update({"exp": str(exp), "sig": b64})
    
    return f"{base}{path}" + (f"?{urlencode(query)}" if query else "")


