from slowapi import Limiter
from slowapi.util import get_remote_address

# Default IP-based key. Swap to a tenant-aware key_func later if needed.
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
